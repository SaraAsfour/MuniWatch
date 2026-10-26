import 'dart:async';

import 'package:flutter/material.dart';

import '../api_client.dart';
import '../util.dart';

class DashboardScreen extends StatefulWidget {
  final VoidCallback onOpenLive;
  const DashboardScreen({super.key, required this.onOpenLive});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? _data;
  String? _error;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
    _timer = Timer.periodic(const Duration(seconds: 15), (_) => _load());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = await ApiClient.instance.dashboard();
      if (!mounted) return;
      setState(() {
        _data = d;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_data == null) {
      if (_error == null) return const Center(child: CircularProgressIndicator());
      return Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Text(_error!),
          const SizedBox(height: 12),
          FilledButton(onPressed: _load, child: const Text('Retry')),
        ]),
      );
    }

    final stats = _data!['quick_stats'] as Map<String, dynamic>;
    final beats = (_data!['device_heartbeats'] as List).cast<Map<String, dynamic>>();
    final online = beats.any((b) => b['status'] == 'online');

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              leading: Icon(Icons.circle,
                  size: 14, color: online ? Colors.greenAccent : Colors.redAccent),
              title: Text(online
                  ? 'Raspberry Pi online'
                  : beats.isEmpty
                      ? 'No device has reported yet'
                      : 'Raspberry Pi offline'),
              subtitle: beats.isEmpty
                  ? null
                  : Text(
                      'Last heartbeat: ${fmtDateTime(parseUtc(beats.first['last_seen'] as String))}'),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: widget.onOpenLive,
              child: AspectRatio(
                aspectRatio: 16 / 9,
                child: Container(
                  color: Colors.black26,
                  child: const Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.videocam, size: 48),
                      SizedBox(height: 8),
                      Text('Hikvision camera · tap for live view'),
                    ],
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(
              child: _StatCard(
                label: 'Traffic events today',
                value: '${stats['vehicles_detected_today']}',
                icon: Icons.directions_car,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _StatCard(
                label: 'Incidents today',
                value: '${stats['incidents_today']}',
                icon: Icons.warning_amber,
              ),
            ),
          ]),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  const _StatCard({required this.label, required this.value, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon),
          const SizedBox(height: 8),
          Text(value, style: Theme.of(context).textTheme.headlineMedium),
          Text(label, style: Theme.of(context).textTheme.bodySmall),
        ]),
      ),
    );
  }
}