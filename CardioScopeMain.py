print ("This is CardioScope")

from PyQt5 import QtGui, QtCore, QtWidgets
from stethoscope_in import audio, set_gui,receive_updated_GUI_values
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import sys
import os
import threading
import numpy as np
import time
import pyaudio
import wave



class cardioscope_gui(QtWidgets.QWidget):
    def __init__(self):
        super(cardioscope_gui, self).__init__()

        self.UI() #Call UI
        self.stream_open_flag = False
        self.init_variables_and_arrays()
        self.init_plot() #Initialize plot, axes, title, etc


    def UI(self):

        #Define Main layout
        self.main_layout = QtWidgets.QVBoxLayout()

        #Define on off Layout
        self.main_on_off_layout = QtWidgets.QHBoxLayout()
        self.sub_on_off_layout = QtWidgets.QVBoxLayout()
        self.sub_on_off_icon_layout = QtWidgets.QVBoxLayout()
        self.main_on_off_layout.addLayout(self.sub_on_off_layout)
        self.main_on_off_layout.addLayout(self.sub_on_off_icon_layout)


        #Define Visualisation Layout
        self.main_visualLayout = QtWidgets.QHBoxLayout()

        #Define Listening mode Layout
        self.main_listenModeLayout = QtWidgets.QVBoxLayout()

        # Define Sonification type Layout
        self.main_SonTypeLayout = QtWidgets.QVBoxLayout()

        # Define Stethoscope control Layout
        self.main_SthControlLayout = QtWidgets.QVBoxLayout()
        self.sub_SthControl_HeaderLayout = QtWidgets.QHBoxLayout()
        self.sub_SthControl_filterLayout = QtWidgets.QHBoxLayout()
        self.sub_SthControl_LevelLayout = QtWidgets.QHBoxLayout()
        self.sub_SthControl_AmpModLayout = QtWidgets.QHBoxLayout()
        self.main_SthControlLayout.addLayout(self.sub_SthControl_HeaderLayout)
        self.main_SthControlLayout.addLayout(self.sub_SthControl_filterLayout)
        self.main_SthControlLayout.addLayout(self.sub_SthControl_LevelLayout)
        self.main_SthControlLayout.addLayout(self.sub_SthControl_AmpModLayout)

        # Add child Layouts to Parent Layout
        self.main_layout.addLayout(self.main_on_off_layout)
        self.main_layout.addLayout(self.main_visualLayout)
        self.main_layout.addLayout(self.main_listenModeLayout)
        self.main_layout.addLayout(self.main_SonTypeLayout)
        self.main_layout.addLayout(self.main_SthControlLayout)

        #-----Font for module titles------#
        font_main = QtGui.QFont()
        font_main.setPointSize(13)
        font_main.setBold(True)
        font_main.setWeight(75)

        #----------------------%---------------------------------#
        #Add buttons to on off module
        self.button_on = QtWidgets.QPushButton('Start CardioScope', self)
        self.button_off = QtWidgets.QPushButton('Stop CardioScope', self)
        self.label_image= QtWidgets.QLabel(self)
        self.label_image.setAlignment(QtCore.Qt.AlignCenter)
        self.pixmap = QtGui.QPixmap('gui_logo.png')
        self.pixmap = self.pixmap.scaledToWidth(150)
        self.label_image.setPixmap(self.pixmap)


        self.sub_on_off_layout.addWidget(self.button_on)
        self.sub_on_off_layout.addWidget(self.button_off)
        self.sub_on_off_icon_layout.addWidget(self.label_image)

        #Step 1:
        #To record a signal instead of using a pre-recorded file activate the following function:
        # self.button_on.clicked.connect(self.start_audio_stream)
        self.button_on.clicked.connect(self.start_pre_recorded_audio_stream)
        self.button_off.clicked.connect(self.close_audio_stream)
        #----------------------%---------------------------------#
        #Add plot to visualisation module

        self.main_figure = ECGFigure(self)
        self.main_visualLayout.addWidget(self.main_figure.canvas)

        # ----------------------%---------------------------------#
        # Add Buttons to Listening mode Module
        self.label_listen_mode = QtWidgets.QLabel("Select listening mode")
        self.label_listen_mode.setFont(font_main)
        self.label_listen_mode.setAlignment(QtCore.Qt.AlignCenter)
        self.btn_listenecg = QtWidgets.QRadioButton('ECG sonification [Stereo]', self)
        self.btn_listensth = QtWidgets.QRadioButton('Stethoscope [Stereo]', self)
        self.btn_listenecgandsth = QtWidgets.QRadioButton('ECG [Left] + Stethoscope [Right]', self)

        self.main_listenModeLayout.addWidget(self.label_listen_mode)
        self.main_listenModeLayout.addWidget(self.btn_listenecg)
        self.main_listenModeLayout.addWidget(self.btn_listensth)
        self.main_listenModeLayout.addWidget(self.btn_listenecgandsth)
        #select a default option
        self.btn_listensth.click()

        #select other listening modes
        self.btn_listenecg.clicked.connect(self.listening_mode_ecg)

        self.btn_listensth.clicked.connect(self.listening_mode_sth)

        self.btn_listenecgandsth.clicked.connect(self.listening_mode_ecgandsth)

        #---- Sonification Type module ----#
        self.label_sonmode = QtWidgets.QLabel ('Select sonification type', self)
        self.label_sonmode.setFont(font_main)
        self.label_sonmode.setAlignment(QtCore.Qt.AlignCenter)
        self.btn_selectmarimba = QtWidgets.QRadioButton('Marimba', self)
        self.btn_selectwater = QtWidgets.QRadioButton('Water Ambience', self)


        self.main_SonTypeLayout.addWidget(self.label_sonmode)
        self.main_SonTypeLayout.addWidget(self.btn_selectwater)
        self.main_SonTypeLayout.addWidget(self.btn_selectmarimba)

        #select sonification methods
        self.btn_selectmarimba.clicked.connect(self.son_type_marimba)
        self.btn_selectwater.clicked.connect(self.son_type_water)

        # ---- Stethoscope control module ----#
        #Labels:
        self.label_controlsth = QtWidgets.QLabel ('Stethoscope settings', self)
        self.label_controlsth.setFont(font_main)
        self.label_controlsth.setAlignment(QtCore.Qt.AlignCenter)
        self.label_filter_slider = QtWidgets.QLabel("Select the cutoff frequency of the lowpass filter [Hz]")
        self.label_level_slider = QtWidgets.QLabel("Select the level of the sound [dB]")
        #Sliders:
        #filter
        self.filter_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.filter_slider.setRange(10,5000)
        self.filter_slider.setValue(2000)
        self.filter_slider.setTickInterval(10)
        self.filter_slider.setSingleStep(10)
        #level
        self.level_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.level_slider.setRange(10, 220)
        self.level_slider.setValue(100)
        self.level_slider.setTickInterval(10)
        self.level_slider.setSingleStep(10)

        #update sliders
        self.filter_slider.valueChanged.connect(self.filter_slider_update)
        self.level_slider.valueChanged.connect(self.level_slider_update)
        #write slider value to labels
        self.filter_slider_cv = self.filter_slider.value()  # Store the value from the slider
        self.filter_slider_text = QtWidgets.QLabel(' Hz ')
        self.filter_slider_text.setText(str(self.filter_slider_cv) +' ' + 'Hz')

        self.level_slider_cv = self.level_slider.value()
        self.level_slider_text = QtWidgets.QLabel(' dB ')
        #amplification factor to db:
        self.level_slider_from_0to2 = (self.level_slider_cv/100.0)
        self.level_slider_in_dB = round(20 * np.log10(self.level_slider_from_0to2), 1)
        # self.level_slider_text.setText(str(self.level_slider_cv))
        self.level_slider_text.setText(str(self.level_slider_in_dB)+' ' + 'dB')

        #add layout elements to GUI
        #Header
        self.sub_SthControl_HeaderLayout.addWidget(self.label_controlsth)
        #Filter
        self.sub_SthControl_filterLayout.addWidget(self.label_filter_slider)
        self.sub_SthControl_filterLayout.addWidget(self.filter_slider)
        self.sub_SthControl_filterLayout.addWidget(self.filter_slider_text)
        #Level
        self.sub_SthControl_LevelLayout.addWidget(self.label_level_slider)
        self.sub_SthControl_LevelLayout.addWidget(self.level_slider)
        self.sub_SthControl_LevelLayout.addWidget(self.level_slider_text)

        # ----------------------%---------------------------------#
        # UI general setup
        self.setLayout(self.main_layout)
        self.setGeometry(650, 650, 650, 650)
        self.setWindowTitle('CardioScope')

    def init_variables_and_arrays(self):
        self.frame_size = 8192#8192 #4096, 8192, 16384
        self.channels = 2
        self.sample_rate = 44100
        self.sthet_amp_data = []
        self.ecg_amp_data = []
        self.send_values = receive_updated_GUI_values(self.sample_rate)
        self.send_values.receive_stethoscope_level_value(self.level_slider_from_0to2)

        # get filter value to update global function in stethoscope_in file
        self.send_values.receive_filter_slider_value(self.filter_slider.value())

    def listening_mode_ecg(self):
        lm = 'ecglistening'
        self.send_values.receive_lm_value(lm)

    def listening_mode_sth(self):
        lm = 'sthlistening'
        self.send_values.receive_lm_value(lm)

    def listening_mode_ecgandsth(self):
        lm = 'ecgandsthlistening'
        self.send_values.receive_lm_value(lm)

    def son_type_marimba(self):
        son = '﻿marimba'
        self.send_values.receive_sonification_type(son)

    def son_type_water(self):
        son = '﻿water'
        self.send_values.receive_sonification_type(son)

    def init_plot(self):
        #Initialize plot

        self.axecg = self.main_figure.figure.add_subplot(211)
        self.axaudio = self.main_figure.figure.add_subplot(212)


        #Create Axis for subplots
        self.axecg.plotECG, = self.axecg.plot([], "r", lw=1, label='')
        self.axecg.axis([0, self.sample_rate, -15000, 15000])


        self.axaudio.plotAudio, = self.axaudio.plot([], "g", lw=1, label='')
        self.axaudio.axis([0, self.sample_rate, -15000, 15000])

        # # labels

        self.axecg.set_title('ECG signal', fontsize=10)
        self.axecg.set_yticks([-15000, 0, 15000])
        self.axecg.tick_params(axis='both', which='major', labelsize=9)
        self.axecg.set_ylabel('Amplitude', fontsize=8)


        self.axaudio.set_title('Stethoscope', fontsize=10)
        # self.axaudio.set_xticks(np.linspace(0,self.sample_rate), 5)
        self.axaudio.set_yticks([-15000, 0, 15000])
        self.axaudio.tick_params(axis='both', which='major', labelsize=9)
        self.axaudio.set_xlabel('Samples', fontsize=8)
        self.axaudio.set_ylabel('Amplitude', fontsize=8)

        self.main_figure.figure.tight_layout()

        #Init plot thread:
        thread_plot = threading.Thread(target=self.update_plot, args=(self.ecg_amp_data,self.sthet_amp_data))
        # thread_plot.start()
    #
    def update_plot(self, ecg_data, stethoscope_data):
        self.winwid = self.sample_rate #Width of plotting window, it is the sample rate
        if len(stethoscope_data) <= self.winwid:
            self.axaudio.plotAudio.set_data(range(len(stethoscope_data)), stethoscope_data)
            self.axecg.plotECG.set_data(range(len(ecg_data)), ecg_data)

        else:
            self.axaudio.plotAudio.set_data(range(self.winwid), stethoscope_data[len(stethoscope_data) - self.winwid:len(stethoscope_data)])
            self.axecg.plotECG.set_data(range(self.winwid),ecg_data[len(ecg_data) - self.winwid:len(ecg_data)])


        self.main_figure.canvas.draw()


    def filter_slider_update(self):
        self.filter_slider_cv = self.filter_slider.value()
        self.filter_slider_text.setText(str(self.filter_slider_cv) +' ' + 'Hz')

        # Update value in the callback function:
        self.send_values.receive_filter_slider_value(self.filter_slider_cv)
        # receive_filter_slider_value(self.filter_slider_cv) #send filter current value

    def level_slider_update(self):
        self.level_slider_cv = self.level_slider.value()
        self.level_slider_from_0to2 = (self.level_slider_cv / 100.0)
        self.level_slider_in_dB = round(20 * np.log10(self.level_slider_from_0to2),1)
        self.level_slider_text.setText(str(self.level_slider_in_dB) +' ' + 'dB')

        #Update value in the callback function:
        self.send_values.receive_stethoscope_level_value(self.level_slider_from_0to2)

    def start_audio_stream(self):
        "This function opens an audio stream to record a stereo signal containing ECG (left channel) and PCG (right channel) recordings"
        self.audio_instance = audio(channels=self.channels, rate=self.sample_rate, frames_per_buffer=self.frame_size, format = pyaudio.paInt16)
        self.audio_instance.start_pyaudio()
        self.audio_instance.start_stream()
        self.stream_open_flag = True #just in case, not used right now.


    def start_pre_recorded_audio_stream(self):
        "This function opens the audio stream using a pre-recorded file containing ECG (left channel) and PCG (right channel) signals "
        #open the audio stream here
        self.currentdir = os.getcwd()
        self.recfilename = 'stethoscope_and_ecg_rec_example.wav'
        self.wf = wave.open(self.currentdir + '/recordings/' + self.recfilename, 'rb')
        self.audio_instance = audio(channels=self.wf.getnchannels(), rate=self.wf.getframerate(), frames_per_buffer=self.frame_size,
                                    format=pyaudio.get_format_from_width(self.wf.getsampwidth()))
        self.audio_instance.start_pyaudio_pre_recorded(self.wf)
        self.audio_instance.start_stream()


    def close_audio_stream(self):
        self.audio_instance.stop_stream()
        time.sleep(1)
        self.audio_instance.close_stream()
        self.stream_open_flag = False

    def receive_audio_amp_values(self, leftChannel, rightChannel):
        #Pending to delete previous samples
        self.ecg_amp_data.extend(leftChannel)
        self.sthet_amp_data.extend(rightChannel)
        self.update_plot(self.ecg_amp_data, self.sthet_amp_data)

class ECGFigure(object):
    def __init__(self, parent):
        self.figure = plt.figure(facecolor='#4da6ff', figsize=(6, 3.5))
        self.canvas = FigureCanvas(self.figure)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main = cardioscope_gui()
    set_gui(main)
    main.show()
    sys.exit(app.exec_())
