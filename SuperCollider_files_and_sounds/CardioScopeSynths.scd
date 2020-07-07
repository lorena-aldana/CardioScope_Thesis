// First step: boot the server
s.boot;
s.reboot; // To rebook the server
//s.freeAll; // To free used nodes

//Marimba sonification
//Load audio files -- Load audio files -- Load audio files -- Load audio files Marimba
(
(
~dirpath = Document.current.dir;
~bmar1 = Buffer.readChannel(s,~dirpath++"/sounds/Marimba.yarn.ff.A3.stereo.aif", bufnum:0);
~bmar2 = Buffer.read(s,~dirpath++"/sounds/Marimba.yarn.ff.C3.stereo.aif",bufnum:1);
~bmar3 = Buffer.read(s,~dirpath++"/sounds/Marimba.yarn.ff.E3.stereo.aif",bufnum:2);
~bmar4 = Buffer.read(s,~dirpath++"/sounds/Marimba.yarn.ff.G3.stereo.aif",bufnum:3);
);
)

(
SynthDef.new(\marimba,{
	arg amp=0.5, out=0, bufnum = 0, rate=1.0, envdur = 0.7, buf;
	var audiosample,signal;

	audiosample=  PlayBuf.ar(2, bufnum, BufRateScale.kr(bufnum)*rate);
	signal=audiosample*amp*EnvGen.kr(Env.perc(attackTime: 0.02, releaseTime: envdur, level: 1, curve: 6), doneAction:2);

	Out.ar(out,signal!2);
}).add;
)

//Test marimba synth
Synth.new(\marimba, [\bufnum, 0, \rate, 1, \envdur, 0.5])

//Water ambience sonification
//Load audio files -- Load audio files -- Load audio files -- Load audio files Water Ambience
(
(
~dirpath = Document.current.dir;
~bf1 = Buffer.readChannel(s,~dirpath++"/sounds/Drop_Main.wav",channels:[0], bufnum:5);
);
)

//Water ambience synth

(
SynthDef(\water, {
	arg amp=1, out=0, rate=1, pan=0, envc=50, envdur =0.4, bufnum;
	var audiosample, signal;

	audiosample=  PlayBuf.ar(1, bufnum, BufRateScale.kr(bufnum)*rate);
	signal=Pan2.ar(audiosample*amp*EnvGen.kr(Env.perc(attackTime: 0.02, releaseTime: envdur, level: 1, curve: 6), doneAction:2), pan);

	//signal=Pan2.ar(signal * amp, pan);
	OffsetOut.ar(out,signal);
}).send(s);
);

//Test water ambience synth:
Synth.new("\water", [\bufnum, 5, \pan, -0.5])