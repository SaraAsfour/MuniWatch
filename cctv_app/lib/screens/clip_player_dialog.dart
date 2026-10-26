import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import '../api_client.dart';

class ClipPlayerDialog extends StatefulWidget {
  final int eventId;
  final String title;
  const ClipPlayerDialog({super.key, required this.eventId, required this.title});
  @override
  State<ClipPlayerDialog> createState() => _ClipPlayerDialogState();
}

class _ClipPlayerDialogState extends State<ClipPlayerDialog> {
  VideoPlayerController? _c;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final url = await ApiClient.instance.clipUrl(widget.eventId);
      final c = VideoPlayerController.networkUrl(Uri.parse(url));
      await c.initialize();
      if (!mounted) {
        await c.dispose();
        return;
      }
      setState(() => _c = c);
      await c.play();
    } catch (e) {
      if (mounted) {
        setState(() => _error =
            'Could not play this clip.\nIf it keeps failing, the clip may not be H.264 encoded.\n$e');
      }
    }
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    return AlertDialog(
      title: Text(widget.title),
      content: SizedBox(
        width: 560,
        child: _error != null
            ? Text(_error!)
            : c == null
                ? const SizedBox(
                    height: 120, child: Center(child: CircularProgressIndicator()))
                : Column(mainAxisSize: MainAxisSize.min, children: [
                    AspectRatio(aspectRatio: c.value.aspectRatio, child: VideoPlayer(c)),
                    const SizedBox(height: 8),
                    VideoProgressIndicator(c, allowScrubbing: true),
                    ValueListenableBuilder<VideoPlayerValue>(
                      valueListenable: c,
                      builder: (_, v, __) => IconButton(
                        iconSize: 36,
                        icon: Icon(v.isPlaying ? Icons.pause : Icons.play_arrow),
                        onPressed: () => v.isPlaying ? c.pause() : c.play(),
                      ),
                    ),
                  ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close')),
      ],
    );
  }
}