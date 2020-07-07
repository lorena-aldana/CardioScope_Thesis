from scipy import signal
import numpy as np
import time
from SuperColliderOSC import SuperColliderClient

global all_data, scserver
all_data = []
scserver = SuperColliderClient()


def set_ecg_thread_values(data_in, sr_in, run_flag_in, timeref, time_info, thld, buf_ecg_data):
    global gl_ecgdata, gl_sr, gl_run_flag, gl_timeref, gl_time_info, bf_thld, buffered_ecg_data
    gl_ecgdata = data_in
    gl_sr = sr_in
    gl_run_flag = run_flag_in
    gl_time_info = time_info
    gl_timeref = timeref
    all_data.extend(gl_ecgdata)
    bf_thld = thld
    buffered_ecg_data = buf_ecg_data

def set_son_values(sontype, amp, pan):
    global sonType, ampValue, panning
    sonType = sontype
    ampValue = amp
    panning = pan


class ecg_scaling(object):
    """This class is to scale and normalize the signals"""

    def __init__(self, ecgdata):
        super(ecg_scaling, self).__init__()
        self.data = ecgdata

    def ecg_to_mv(self):
        '''To do: solve the scaling calculation, value of sensor to digital output of interface'''
        vcc = 3.7
        gain_sensor = 1100
        n_bits_channel = 2 ** 16
        return ((self.data * vcc / n_bits_channel - vcc / 2) / gain_sensor) * 1100

    def ecg_normalize(self):
        return self.data / np.max(np.abs(self.data))


class ecgsig_proc_2(object):
    """This is the class for processing ecg signals"""

    def __init__(self, samplerate):
        super(ecgsig_proc_2, self).__init__()
        global gl_ecgdata, gl_sr, gl_run_flag, one_second, gl_databuffer, gl_time
        global sonType, ampValue, panning
        self.samplerate = samplerate
        gl_ecgdata = []
        gl_run_flag = []
        gl_sr = []
        one_second = self.samplerate
        gl_databuffer = []
        self.frame_size = np.shape(gl_ecgdata)
        sonType = 'marimba';
        ampValue = 0.0;
        panning = 0.0

    def r_peak_RT_det(self):

        while True:

            if gl_run_flag == True:

                self.find_R_peaks(buffered_ecg_data[-self.samplerate:], window=int(self.samplerate/8), thpercentage=0.65, plot=True)
                time.sleep(0.1)


            elif gl_run_flag == False:
                break

    def bpIIR_filter(self, data, fc1=0.1, fc2=70, order=2):
        '''This function filters (bandpass) the ECG signal
        and removes the DC component'''
        # Band pass filter design
        # Remove DC component
        sig_centered = data - np.mean(data)
        sigarr = sig_centered
        cutoffpass = fc1 / (self.samplerate / 2.0);
        cutoffstop = fc2 / (self.samplerate / 2.0)  # 5.0 inferior cf, 70.0
        b, a = signal.iirfilter(order, [cutoffpass, cutoffstop], btype='bandpass', analog=False, ftype='butter')
        # Apply Bandpass pass filter
        signalfilt = signal.filtfilt(b, a, sigarr[:])
        return signalfilt

    def lpIIR_filter(self, fc1, order=2):
        # Remove DC component
        sig_centered = self.data - np.mean(self.data)
        # Filter signal
        cutoffpass = fc1 / (self.samplerate / 2.0);
        b, a = signal.iirfilter(order, cutoffpass, btype='low', analog=False, ftype='butter')
        signalfilt = signal.filtfilt(b, a, sig_centered, method='gust')
        return signalfilt

    def notch_filter(self, data, fc1=50, Q=1.0):
        notchfreq = fc1 / (self.samplerate / 2.0);
        b, a = signal.iirnotch(notchfreq, Q)
        signalfilt = signal.filtfilt(b, a, data)
        return signalfilt

    def hilbert_transform(self, sig):
        # # Hilbert transform
        ht = abs(signal.hilbert(sig))
        return ht

    def bandpassIIR_filter(self, data, sr=44100, fc1=0.1, fc2=70, order=2):
        '''This function filters (bandpass) the ECG signal
        and removes the DC component'''
        # Band pass filter design
        cutoffpass = fc1 / (sr / 2.0);
        cutoffstop = fc2 / (sr / 2.0)  # 5.0 inferior cf, 70.0
        b, a = signal.iirfilter(order, [cutoffpass, cutoffstop], btype='bandpass', analog=False, ftype='butter')
        # Apply bandpass pass filter
        signalfilt = signal.filtfilt(b, a, data[:])
        return signalfilt

    def R_peaks_detection_window(self, ampdata, timedata, thld):

        '''This function chooses one peak in the given time window.
        It is the core function in ecgprocpy3 for calculating R peaks'''
        detected_peaks = []
        lastPeak = []
        above_threshold = False
        for x in range(len(ampdata)):
            last_above_thrld = above_threshold
            curValue = ampdata[x]
            if curValue > thld:
                above_threshold = True
            else:
                above_threshold = False

            if above_threshold == True:
                if len(lastPeak) == 0 or curValue > lastPeak[1]:
                    lastPeak = [timedata[x], ampdata[x]]
            if last_above_thrld == True and above_threshold == False:
                detected_peaks.append(lastPeak)
                lastPeak = []

            last_above_thrld = above_threshold

        if len(detected_peaks) > 0:  # select max peak among peaks found in window
            peakamp, loc = max([(x[1], i) for i, x in enumerate(detected_peaks)])
            selectedpeak = detected_peaks[loc]
            return selectedpeak

    def r_peak_found(self):
        global sonType, ampValue, panning
        print('QRS complex found')
        #To sonify the R peak
        synth_name = sonType
        scserver.sc_msg("s_new", [synth_name, -1, 1, 0, "buf", 8, 'amp', ampValue, 'pan', panning])

    # def find_R_peaks(self, data, run_flag=False, window=200, thpercentage=0.65, plot=False):
    #     '''This function filters the signal, calculates the time stamps for the peaks function and find
    #     the R peaks in one ECG lead'''
    #     global tref
    #     tref = 0.0
    #     # Find R peaks
    #     # peaks_final_sel=[]
    #     while True:
    #
    #         if len(all_data) >= one_second:
    #             print('One second of data stored')
    #             if gl_run_flag == True:
    #
    #                 # data = all_data[-44000:]
    #                 flag = gl_run_flag
    #                 # print ('Thread is listening')
    #                 # print(('Run flag is %s')%(flag))
    #                 # print(data[-5:])
    #
    #                 sig = all_data[-one_second:]
    #
    #                 # ----Test the process without the filtering and without the hb transform, to reduce computing power:-----
    #
    #                 # Filter the signal
    #                 sigf = self.bandpassIIR_filter(sig, self.samplerate, fc1=5, fc2=70, order=2)
    #                 # Hilbert transform
    #                 ht = self.hilbert_transform(sigf)
    #
    #                 # Set threshold for peaks detection
    #                 maxamp = np.max(ht)
    #                 minamp = np.min(ht)
    #                 thld = (np.abs(maxamp - minamp) * thpercentage)  # Threshold is 75 of the amplitude in the signal
    #                 sig = ht  # now the sig variable contains the hilbert transform
    #
    #                 # ----Test the process without the filtering and without the hb transform, to reduce computing power:------
    #                 # thld = 6000
    #
    #
    #                 # Calculate time stamps
    #                 # tref = 0.0
    #                 tlist = []  # Initialize list for timestamps
    #                 dtsamples = (1.0 / self.samplerate)  # Time between samples
    #                 peaks = []
    #                 peaks_final_sel = []
    #                 size_an_window = window
    #                 # time_stamps_second = np.linspace(0, one_second/self.samplerate, one_second)
    #                 for count, element in enumerate(sig, 1):  # Start counting from 1
    #                     if count % size_an_window == 0:
    #                         segment = sig[count - size_an_window:count]
    #                         for x in range(len(segment)):  # Create time stamps according to sample rate
    #                             tlist.append(tref)
    #                             tref = tref + dtsamples
    #                         times = tlist[len(tlist) - size_an_window:len(tlist)]
    #                         peak_found = self.R_peaks_detection_window(segment, times,
    #                                                                    thld)  # Calculate peaks in window
    #
    #                         # If a new peak is found
    #                         if peak_found is not None:
    #                             print('printing r peaks found')
    #                             print(peak_found)
    #                             self.r_peak_found()
    #                         peaks.append(peak_found)
    #                 peaks_final_sel = [x for x in peaks if x is not None]  # Time, amplitude
    #                 r_in_samples = [x[0] * self.samplerate for x in peaks_final_sel]  # Peak location in samples
    #
    #                 time.sleep(0.05)
    #             # print ('printing R peaks:')
    #             # print (peaks_final_sel)
    #             # print(len(peaks_final_sel))
    #
    #             elif gl_run_flag == False:
    #                 break
    #                 # else:
    #                 # 	time.sleep(2) #wai until the buffer is filled with one second of data
    #
    #     return

    def find_R_peaks(self, data, window=200, thpercentage=0.65, plot=False):
        '''This function filters the signal, calculates the time stamps for the peaks function and find
        the R peaks in one ECG lead'''
        global tref
        tref = 0.0

        sig = data

        # if plot == True:
        #
        # 	plt.figure()
        # 	plt.plot(sig)

        # ----Test the process without the filtering and without the hb transform, to reduce computing power:-----

        # Filter the signal
        sigf = self.bandpassIIR_filter(sig, self.samplerate, fc1=5, fc2=70, order=2)
        # Hilbert transform
        ht = self.hilbert_transform(sigf)

        # Set threshold for peaks detection
        # the threshold is calculated in the audio stream callback function
        thld = bf_thld

        sig = ht  # now the sig variable contains the hilbert transform

        # ----Test the process without the filtering and without the hb transform, to reduce computing power:------

        # Calculate time stamps
        tlist = []  # Initialize list for timestamps
        dtsamples = (1.0 / self.samplerate)  # Time between samples
        peaks = []
        # peaks_final_sel = []
        size_an_window = window
        # time_stamps_second = np.linspace(0, one_second/self.samplerate, one_second)
        for count, element in enumerate(sig, 1):  # Start counting from 1
            if count % size_an_window == 0:
                segment = sig[count - size_an_window:count]
                for x in range(len(segment)):  # Create time stamps according to sample rate
                    tlist.append(tref)
                    tref = tref + dtsamples
                times = tlist[len(tlist) - size_an_window:len(tlist)]
                peak_found = self.R_peaks_detection_window(segment, times, thld)  # Calculate peaks in window

                # If a new peak is found
                if peak_found is not None:
                    self.r_peak_found()
                    peaks.append(peak_found)
                    break
        # peaks_final_sel = [x for x in peaks if x is not None]  # Time, amplitude

        return

