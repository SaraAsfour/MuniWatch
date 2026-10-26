import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:http/http.dart' as http;

import '../config.dart';

class LiveScreen extends StatefulWidget {
  const LiveScreen({super.key});
  @override
  State<LiveScreen> createState() => _LiveScreenState();
}

class _LiveScreenState extends State<LiveScreen> {
  final RTCVideoRenderer _renderer = RTCVideoRenderer();
  RTCPeerConnection? _pc;
  bool _connected = false;
  String _status = 'Connecting…';
  String? _error;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    await _renderer.initialize();
    await _connect();
  }

  @override
  void dispose() {
    _pc?.close();
    _renderer.dispose();
    super.dispose();
  }

  Future<void> _waitForIce(RTCPeerConnection pc) async {
    final end = DateTime.now().add(const Duration(seconds: 3));
    while (pc.iceGatheringState !=
            RTCIceGatheringState.RTCIceGatheringStateComplete &&
        DateTime.now().isBefore(end)) {
      await Future.delayed(const Duration(milliseconds: 100));
    }
  }

  Future<void> _connect() async {
    await _pc?.close();
    _pc = null;
    if (!mounted) return;
    setState(() {
      _error = null;
      _connected = false;
      _status = 'Connecting…';
    });

    try {
      final pc = await createPeerConnection({
        'iceServers': <Map<String, dynamic>>[],
        'sdpSemantics': 'unified-plan',
      });
      _pc = pc;

      pc.onTrack = (RTCTrackEvent e) {
        if (!mounted || e.streams.isEmpty) return;
        setState(() {
          _renderer.srcObject = e.streams[0];
          _connected = true;
          _status = 'Live';
        });
      };

      await pc.addTransceiver(
        kind: RTCRtpMediaType.RTCRtpMediaTypeVideo,
        init: RTCRtpTransceiverInit(direction: TransceiverDirection.RecvOnly),
      );

      final offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      await _waitForIce(pc);
      final local = await pc.getLocalDescription();

      // go2rtc answers a raw SDP offer posted to /api/webrtc
      final resp = await http.post(
        Uri.parse('$go2rtcBase/api/webrtc?src=$cameraStream'),
        headers: {'Content-Type': 'application/sdp'},
        body: local!.sdp,
      );
      if (resp.statusCode != 200 && resp.statusCode != 201) {
        throw 'go2rtc returned HTTP ${resp.statusCode}';
      }
      var answerSdp = resp.body;
      if (answerSdp.trimLeft().startsWith('{')) {
        answerSdp = (jsonDecode(answerSdp) as Map<String, dynamic>)['sdp'] as String;
      }
      await pc.setRemoteDescription(RTCSessionDescription(answerSdp, 'answer'));
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Could not open the live stream.\n$e';
        _status = 'Disconnected';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        AspectRatio(
          aspectRatio: 16 / 9,
          child: Container(
            color: Colors.black,
            alignment: Alignment.center,
            child: _connected
                ? RTCVideoView(
                    _renderer,
                    objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitContain,
                  )
                : Padding(
                    padding: const EdgeInsets.all(16),
                    child: _error != null
                        ? Text(_error!, textAlign: TextAlign.center)
                        : const CircularProgressIndicator(),
                  ),
          ),
        ),
        const SizedBox(height: 12),
        Row(children: [
          Icon(Icons.circle,
              size: 12, color: _connected ? Colors.greenAccent : Colors.orangeAccent),
          const SizedBox(width: 8),
          Text(_status),
          const Spacer(),
          OutlinedButton.icon(
            onPressed: _connect,
            icon: const Icon(Icons.refresh),
            label: const Text('Reconnect'),
          ),
        ]),
        const SizedBox(height: 16),
        Text(
          'While you watch, the server keeps running Tier 2 analysis (YOLOv8 + MediaPipe) '
          'on the stream in the background.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}