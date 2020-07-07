from scipy import signal
import numpy as np


class scaling(object):
    """This class is to scale and normalize the signals"""

    def __init__(self, data):
        super(scaling, self).__init__()
        self.data = data

    def normalize(self):
        return self.data / np.max(np.abs(self.data))


class sthsig_proc(object):
    """Class for sthethoscope analysis"""

    def __init__(self, data, samplerate):
        super(sthsig_proc, self).__init__()
        self.sthsig = data
        self.samplerate = samplerate

    def lpIIR_filter(self, fc1, order=4):
        # Remove DC component
        sig_centered = self.sthsig - np.mean(self.sthsig)
        # Filter signal
        cutoffpass = fc1 / (self.samplerate / 2.0);
        b, a = signal.iirfilter(order, cutoffpass, btype='low', analog=False, ftype='butter')
        signalfilt = signal.filtfilt(b, a, sig_centered, method='gust')
        # signalfilt = signal.lfilter(b, a, data)
        return signalfilt

    def bpIIR_filter(self, fc1=0.1, fc2=70, order=4):
        '''This function filters (bandpass) the ECG signal
        and removes the DC component'''
        # Band pass filter design
        # Remove DC component
        sig_centered = self.sthsig - np.mean(self.sthsig)
        sigarr = sig_centered

        cutoffpass = fc1 / (self.samplerate / 2.0);
        cutoffstop = fc2 / (self.samplerate / 2.0)  # 5.0 inferior cf, 70.0
        b, a = signal.iirfilter(order, [cutoffpass, cutoffstop], btype='bandpass', analog=False, ftype='butter')
        # Apply High pass filter
        signalfilt = signal.filtfilt(b, a, sigarr[:])
        return signalfilt

    def hilbert_transform(self, sig):
        # # Hilbert transform
        ht = abs(signal.hilbert(sig))
        return ht

    def running_mean(self, x, N):
        cumsum = np.cumsum(np.insert(x, 0, 0))
        return (cumsum[N:] - cumsum[:-N]) / float(N)


class sth_features(object):
    """docstring for ClassName"""

    def __init__(self, data, samplerate):
        super(sth_features, self).__init__()
        self.data = data
        self.samplerate = samplerate

    def onset_detection_window(self, ampdata, timedata, thld):

        '''This function chooses one onset in the given time window.
        It is the core function in ecgprocpy3 for calculating R onsets'''

        detected_onsets = []
        lastOnset = []
        aboveThreshold = False
        for x in range(len(ampdata)):
            lastAboveThreshold = aboveThreshold
            curValue = ampdata[x]
            if curValue > thld:
                aboveThreshold = True
            else:
                aboveThreshold = False

            if aboveThreshold == True:
                if len(lastOnset) == 0 or curValue > lastOnset[1]:
                    lastOnset = [timedata[x], ampdata[x]]
            if lastAboveThreshold == True and aboveThreshold == False:
                detected_onsets.append(lastOnset)
                lastOnset = []

            lastAboveThreshold = aboveThreshold

        if len(detected_onsets) > 0:  # select max onset among onsets found in window
            onsetamp, loc = max([(x[1], i) for i, x in enumerate(detected_onsets)])
            selectedonset = detected_onsets[loc]
            return selectedonset

    def find_Onsets(self, window=200, thpercentage=0.65):
        '''This function filters the signal, calculates the time stamps for the onsets function and find
        the R onsets in one stethoscope recording'''
        # Filter the signal using the processing class
        sig_p = sthsig_proc(self.data, self.samplerate)
        sig_f = sig_p.bpIIR_filter(fc1=20, fc2=80)
        # Hilbert transform
        ht = sig_p.hilbert_transform(sig_f)

        # Set threshold for onsets detection
        maxamp = np.max(ht)
        minamp = np.min(ht)
        thld = (np.abs(maxamp - minamp) * thpercentage)  # Threshold is 75 of the amplitude in the signal

        #
        originalsigtoplot = self.data
        sig = ht  # now the sig variable contains the hilbert transform

        # Calculate time stamps
        tref = 0.0
        tlist = []  # Initialize list for timestamps
        dtsamples = (1 / self.samplerate)  # Time between samples
        onsets = []
        onsets_final_sel = []
        size_an_window = window
        for count, element in enumerate(sig, 1):  # Start counting from 1
            if count % size_an_window == 0:
                segment = sig[count - size_an_window:count]  # Only calculate onsets of the first channel
                for x in range(len(segment)):  # Create time stamps accroding to sample rate
                    tlist.append(tref)
                    tref = tref + dtsamples
                times = tlist[len(tlist) - size_an_window:len(tlist)]
                onset_found = self.onset_detection_window(segment, times, thld)  # Calculate onsets in window
                onsets.append(onset_found)
        onsets_final_sel = [x for x in onsets if x is not None]  # Time, amplitude
        r_in_samples = [x[0] * self.samplerate for x in onsets_final_sel]  # onset location in samples

        return onsets_final_sel


