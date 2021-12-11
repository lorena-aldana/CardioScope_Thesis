from scipy import signal
import numpy as np
import time
from SuperColliderOSC import SuperColliderClient

global all_data, scserver
all_data = []
#create instance of SuperCollider class
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

def set_son_values(sontype, amp, pan, listeningmode):
    global sonType, ampValue, panning, lmode
    sonType = sontype
    ampValue = amp
    panning = pan
    lmode = listeningmode
    print(lmode, sonType, ampValue, panning)


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
        global sonType, ampValue, panning, lmode
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
        lmode = ' '

    def r_peak_RT_det(self):

        while True:

            if gl_run_flag == True:

                self.find_R_peaks(buffered_ecg_data[-self.samplerate:], window=int(self.samplerate))
                time.sleep(int(self.samplerate/self.samplerate))

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

    def R_peaks_detection_window(self, ampdata, thld):
        '''This function chooses one peak in the given time window.
        It is the core function in ecgprocpy3 for calculating R peaks'''
        thld = thld
        detected_peaks = []
        lastPeak = 0
        selectedpeak = None
        above_threshold = False
        last_above_thrld = False
        for x in range(len(ampdata)):
            curValue = ampdata[x]
            if curValue > thld:
                above_threshold = True
            else:
                above_threshold = False

            if above_threshold == True:
                if curValue > lastPeak:
                    lastPeak = ampdata[x]

            if last_above_thrld == True and above_threshold == False:
                detected_peaks.append(lastPeak)
                lastPeak = []

            last_above_thrld = above_threshold

        if len(detected_peaks) > 0:  # select max peak among peaks found in window
            peakamp, loc = max([(x, i) for i, x in enumerate(detected_peaks)])
            selectedpeak = detected_peaks[loc]

            return selectedpeak

    def r_peak_found(self):
        global sonType, ampValue, panning, lmode
        # print('QRS complex found')
        #To sonify the R peak:
        synth_name = sonType
        mode= lmode
        if mode == 'ecglistening':
            if sonType == 'marimba':
                scserver.sc_msg("s_new", [synth_name, -1, 1, 0, "buf", np.random.randint(0,3), 'amp', 0.2, 'pan', panning])
            elif sonType == 'water':
                scserver.sc_msg("s_new", [synth_name, -1, 1, 0, "buf", 5, 'amp', 3.0, 'pan', 0.0])
        if mode == 'ecgandsthlistening':
            panning = -1
            if sonType == 'marimba':
                scserver.sc_msg("s_new", [synth_name, -1, 1, 0, "buf", np.random.randint(0,3), 'amp', 0.2, 'pan', panning])
            elif sonType == 'water':
                scserver.sc_msg("s_new", [synth_name, -1, 1, 0, "buf", 5, 'amp', 3.0, 'pan', panning])


    def find_R_peaks(self, data, window):
        '''This function filters the signal, calculates the time stamps for the peaks function and find
        the R peaks in one ECG lead'''
        sig = data
        peak_found = []

        # ----Test the process without the filtering and without the hb transform, to reduce computing power:-----

        # Filter the signal
        sigf = self.bandpassIIR_filter(sig, self.samplerate, fc1=5, fc2=40, order=2)
        # Hilbert transform
        ht = self.hilbert_transform(sigf)

        # Set threshold for peaks detection
        # the threshold is calculated in the audio stream callback function based on the last three seconds of ECG data
        thld = bf_thld
        sig = ht  # now the sig variable contains the hilbert transform, thus the threshold changes

        # for count, element in enumerate(sig, 1):  # Start counting from 1
        #     if count % window == 0:
        peak_found = self.R_peaks_detection_window(sig, thld)  # Calculate peaks in window

        # If a new peak is found
        if peak_found is not None:
            self.r_peak_found()
            return


