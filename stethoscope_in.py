import pyaudio
import numpy as np
import time
import threading
import scipy.signal as signal
from ecgprocpy3Class import ecg_scaling, ecgsig_proc_2
from ecgprocpy3Class import set_ecg_thread_values
from ecgprocpy3Class import set_son_values

def set_gui(this_gui):
    global gui
    gui = this_gui

class receive_updated_GUI_values(object):
    def __init__(self, rate = 44100):
        global listeningmode, sonType, amp
        listeningmode = 'sthlistening'
        sonType = 'marimba'
        amp = 0.0
        self.val_sr = rate

    def receive_stethoscope_level_value(self, level):
        global stethoscope_level_value
        stethoscope_level_value = level
        print (('level value received: %s') % (stethoscope_level_value))

    def receive_filter_slider_value(self, value):
        global filter_cutoff
        filter_cutoff = value
        self.update_filter_values(filter_cutoff)

    def update_filter_values(self,fc):
        global a, b, zi
        fs = self.val_sr
        a = [1, -np.exp(-2 * np.pi * fc / fs)]
        b = [1 - np.exp(-2 * np.pi * fc / fs)]
        zi = signal.lfiltic(b, a, [0])

    def receive_lm_value(self, lm):
        global listeningmode, amp
        listeningmode= lm

        if listeningmode == 'ecglistening':
            amp = 0.5
            pan = 0.0
        elif listeningmode == 'ecgandsthlistening':
            amp = 0.5
            pan = -1.0
        elif listeningmode == 'sthlistening':
            amp = 0.0
            pan = 0.0

        set_son_values(sonType, amp, pan)

    def receive_sonification_type(self, son):
        global sonType, listeningmode, amp
        sonType = son

        if listeningmode == 'ecglistening':
            amp = 0.5
            pan = 0.0
        elif listeningmode == 'ecgandsthlistening':
            amp = 0.5
            pan = -1.0
        elif listeningmode == 'sthlistening':
            amp = 0.0
            pan = 0.0

        set_son_values(sonType, amp, pan)


class audio(object):
    'Class to input and process audio'

    def __init__(self, channels=2, rate=44100, frames_per_buffer=2048, format = pyaudio.paInt16):
        global sr, _ecg_data, ecgproc, ecgscale, timeref
        timeref = time.time()
        self.ecg_buf = []
        self.format = format
        self.channels = channels
        self.audio_sr = rate
        self.frames = frames_per_buffer
        self.buffer = []
        self.filter_cutoff = 1000
        self._ecg_data = []
        self.run_flag = False
        self.start_level_value = 0.0
        #call the amplitude mod function on start
        self.mod_signal = self.amplitude_mod()
        self.diff = 0
        self.buf_pt_start = 0
        self.buf_pt_end = self.buf_pt_start + self.frames
        self.thld = 0
        self.buffered_ecgdata = []

    def start_pyaudio(self):
        self.audio = pyaudio.PyAudio()

        #print characteristics of the audio system:
        print('Audio system info:')
        print(self.audio.get_device_count())
        print(self.audio.get_default_input_device_info())
        print(self.audio.get_device_info_by_index(0))
        print(self.audio.get_device_info_by_index(1))
        print(self.audio.get_device_info_by_index(2))
        print(self.audio.get_device_info_by_index(3))


        self.stream = self.audio.open(format=pyaudio.paInt16,
                        channels=self.channels,
                        rate=self.audio_sr,
                        output=True,
                        input=True,
                        frames_per_buffer=self.frames,
                        stream_callback=self.callback)

    def start_pyaudio_pre_recorded(self, wave):
        print('Starting pre_recorded audio')
        self.audio = pyaudio.PyAudio()
        self.wf = wave
        self.stream = self.audio.open(format=self.format,
                      channels=self.channels,
                      rate=self.audio_sr,
                      output=True,
                      frames_per_buffer=self.frames,
                      stream_callback=self.callback_pre_recorded)


        #start thread to find R peaks
        self.ecgproc = ecgsig_proc_2(self.audio_sr)
        # self.thread_ecg = threading.Thread(target=self.ecgproc.find_R_peaks,args=(self._ecg_data, self.run_flag, 200, 0.8, False))
        self.thread_ecg = threading.Thread(target=self.ecgproc.r_peak_RT_det,args=())
        ## To detect -and sonify- the R peaks, start the thread
        # self.thread_ecg.start()
        self.run_flag = True


    def start_stream(self):
        self.init_filter(self.filter_cutoff, self.audio_sr)
        self.stream.start_stream()


    def stop_stream(self):
        self.run_flag = False
        set_ecg_thread_values(self._ecg_data, self.audio_sr, self.run_flag, timeref, self.time_info['current_time']+timeref, self.thld, self.buffered_ecgdata)
        self.stream.stop_stream()


    def close_stream(self):
        self.stream.close()
        self.audio.terminate()

    def running_mean(self,x, N):
        cumsum = np.cumsum(np.insert(x, 0, 0))
        return (cumsum[N:] - cumsum[:-N]) / float(N)

    def volume_smooth(self):
        "Function to create smooth transitions whene there are level changes in the stethoscope signal"
        len_smooth_signal = self.frames
        self.smo_sig = np.linspace(self.start_level_value, stethoscope_level_value, len_smooth_signal)
        self.start_level_value = stethoscope_level_value

        return self.smo_sig

    def get_amp_mod_buffer(self):

        if self.buf_pt_end <= self.len_amp_mod:
            self.mod_buf_sel = self.modulated_smooth[self.buf_pt_start:self.buf_pt_end] #select chunk of modulation signal
            #update buffer pointers
            self.buf_pt_start = self.buf_pt_end
            self.buf_pt_end = self.buf_pt_start + self.frames


        elif self.buf_pt_end > self.len_amp_mod:

            self.diff = self.buf_pt_end-self.len_amp_mod
            self.mod_buf_sel = np.hstack((self.modulated_smooth[self.buf_pt_start:self.len_amp_mod],self.modulated_smooth[0:self.diff]))
            #update buffer pointers
            self.buf_pt_start = 0 + self.diff
            self.buf_pt_end = self.buf_pt_start + self.frames

        return self.mod_buf_sel


    def amplitude_mod(self):
        """Amplitude modulation function
        Currently is not implemented in real-time. The offline version is available as a Jupyter Notebook"""

        self.len_amp_mod = self.audio_sr #it should depend on the HR
        #init mod buffer
        self.mod = [0] * self.len_amp_mod
        #create the amp mod signal (long)
        mod_win_start = 0
        mod_win_end = mod_win_start + int(self.frames) # one second
        # %-----------------window---------------------------
        # define window type for the modulation
        window = np.hanning(mod_win_end - mod_win_start)
        # ramp
        #         window = np.linspace(0, 0.9, t_e - t_b)
        #         damp
        #         window = np.linspace(0.9, 0, t_e - t_b)
        # hamming
        #         window = np.hamming(t_e - t_b)
        # modulation

        #Refer to the CardioScope paper for a deeper explanation on the following parameters:
        gain = 2
        background = 0.2

        self.mod[mod_win_start:mod_win_end] = gain * window  # window starts from Rpeak
        self.mod[mod_win_end:self.len_amp_mod] = [background] * (self.len_amp_mod - mod_win_end)

        #smooth modulation
        self.modulated_smooth = []
        n = 200
        #this is the modulated amplitude signal
        self.modulated_smooth = self.running_mean(np.concatenate(([0] * (n - 1), self.mod)), n)

        return self.modulated_smooth

    def ecg_buffer(self, data):

        #Add data to buffer
        self.ecg_buf.extend(data)

        #Create an array with three seconds of data
        if len(self.ecg_buf) <= (int(self.audio_sr*3)):
            pass
        else:
            #Store only the last three seconds of data
            trimmed_ecg_buffer = self.ecg_buf[-int(self.audio_sr*3):]
            self.ecg_buf = trimmed_ecg_buffer

        buf_thld = np.max(self.ecg_buf)*0.95

        return self.ecg_buf, int(buf_thld)




    def callback_pre_recorded(self, in_data, frame_count, time_info, status):

        '''This function is used to show CardioScope and its functionalities using pre-recorded data. 
        It doesn't create a new audio file. But it allows user to test the GUI parameters in real-time. '''

        global a, b, zi
        self.read_from_wave = self.wf.readframes(frame_count) #Bytes
        self.data = np.frombuffer(self.read_from_wave , dtype=np.int16)
        #---------------Processing for pre recorded signal goes here --------------

        self.y = self.data

        # -----------Data is interleaved, thus separate left and right channels-----------

        chunk_length = int(len(self.y) / self.channels)
        self.reshape_data = np.reshape(self.y, (chunk_length, self.channels))
        self.ecg_ch = [x[0] for x in self.reshape_data]
        self.sth_ch = [x[1] for x in self.reshape_data]

        #--------feature detection------------------
        #Find ECG R peaks
        #Make a copy of the ECG data array
        self._ecg_data = self.ecg_ch
        # self.thread_ecg.join()
        # -------------R peak finding -----------------------
        #add data to ecg buffer
        self.buffered_ecgdata, self.thld = self.ecg_buffer(self._ecg_data)

        # run_flag = True
        self.time_info = time_info
        set_ecg_thread_values(self._ecg_data, self.audio_sr, self.run_flag, timeref, self.time_info['current_time']+timeref, self.thld, self.buffered_ecgdata)

        # -----------Filter per channel ------------
        self.sth_filtered, zi = signal.lfilter(b, a, self.sth_ch, zi=zi)

        # -----------volume control -----------
        #call volume smooth signal
        self.smooth_level = self.volume_smooth()


        self.left = self.ecg_ch
        #Smooth volume changes
        self.right = self.sth_filtered * self.smooth_level
        # Tip: print(np.max(self.right))# ---> Max should be 32768, otherwise it will clip

        # # -------------Amplitude modulation [Not yet implemented in real-time]-----------------
        
        #Amplitude modulation signal according to parameters given by the user
        # amp_mod_buf_signal = self.get_amp_mod_buffer()
        #Modulate the stethoscope signal
        # self.right = self.sth_filtered * amp_mod_buf_signal

        # -----------Combine left right after volume control
        if listeningmode == 'sthlistening':
            self.LR = self.outputLR(frame_count, self.right, self.right)
        elif listeningmode == 'ecglistening':
            self.null = np.linspace(stethoscope_level_value,0,frame_count)
            self.LR = self.outputLR(frame_count, self.null , self.null)
        elif listeningmode == 'ecgandsthlistening':
            self.null = np.linspace(0,stethoscope_level_value,frame_count)
            self.LR = self.outputLR(frame_count, self.null , self.right)

        # -----------Convert output array to bytes-----------
        audio_output = self.LR.astype(np.int16)

        # -----------call values tunnel function/communicates to main GUI---------
        #to plot unfiltered und unleveled values
        # self.audio_amp_values_tunnel(self.ecg_ch, self.sth_ch)
        self.audio_amp_values_tunnel(self.ecg_ch, self.sth_ch)


        return (audio_output.tobytes(), pyaudio.paContinue)


    def init_filter(self, fc, fs):
        '''Function to calculate the coefficients according to the parameters given by the user'''
        global a, b, zi
        a = [1, -np.exp(-2 * np.pi * fc / fs)]
        b = [1 - np.exp(-2 * np.pi * fc / fs)]
        zi = signal.lfiltic(b, a, [0])

    def callback(self, in_data, frame_count, time_info, status):
        global a, b, zi

        #------------Concatenate the bytes stream-------------
        #-----------convert byte data to ndarray --------
        self.data = np.frombuffer(in_data, dtype=np.int16)


        # -----------Audio Processing --------
        #Filter
        self.y, zi = signal.lfilter(b, a, self.data, zi=zi)
        # -----------Data is interleaved, thus separate left and right channels-----------
        chunk_length = int(len(self.y) / self.channels)
        self.reshape_data = np.reshape(self.y, (chunk_length, self.channels))
        self.left_ch = [x[0] for x in self.reshape_data]
        self.right_ch = [x[1] for x in self.reshape_data]

        # -----------volume control -----------
        self.left = self.left_ch
        self.right = [x * stethoscope_level_value for x in self.right_ch]


        #-------------Here would be the amplitude modulation real-time implementation

        #

        # -----------Combine left right after volume control
        self.LR = self.outputLR(frame_count, self.left, self.right)



        #-----------Convert output array to bytes-----------
        audio_output = self.LR.astype(np.int16)

        #-----------call values tunnel function/communicates to main GUI---------
        self.audio_amp_values_tunnel(self.left_ch, self.right_ch)


        return (audio_output.tobytes(), pyaudio.paContinue)

    def outputLR(self, frame_length, left_ch, right_ch):
        "Creates ouput form left and right channels"

        #Prepare output array
        self.output = np.zeros(frame_length * 2)

        for sample in range(0, frame_length * 2):
            #Separate left and right channels
            # print(sample)
            if sample % 2:
                self.output[sample] = right_ch[(int)(sample / 2)]
                # print(right_ch[int(sample/2)])
                # print (right_ch[(int)(sample / 2)])
            else:
                self.output[sample] = left_ch[(int)(sample / 2)]

        return self.output


    def audio_amp_values_tunnel(self, leftChannel, rightChannel):
        "This function communicates with the GUI functions in order to plot acquired data"
        gui.receive_audio_amp_values(leftChannel, rightChannel)
