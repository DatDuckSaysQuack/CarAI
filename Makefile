.PHONY: aec3 run
aec3:
	gcc -shared -fPIC -O3 -o libaec3shim.so aec3shim.c -lwebrtc_audio_processing

run:
	python3 run.py
