import 'package:flutter/material.dart';

import '../api_client.dart';
import '../util.dart';
import 'clip_player_dialog.dart';

class EventsScreen extends StatefulWidget {
  const EventsScreen({super.key});
  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsScreenState extends State<EventsScreen> {
  String? _category; // null = all
  late Future<List<dynamic>> _future = ApiClient.instance.events();

  void _reload() {
    setState(() {
      _future = ApiClient.instance.events(category: _category);
    });
  }

  void _setCategory(String? c) {
    _category = c;
    _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          child: Wrap(spacing: 8, children: [
            ChoiceChip(
                label: const Text('All'),
                selected: _category == null,
                onSelected: (_) => _setCategory(null)),
            ChoiceChip(
                label: const Text('Crimes'),
                selected: _category == 'crime',
                onSelected: (_) => _setCategory('crime')),
            ChoiceChip(
                label: const Text('Traffic violations'),
                selected: _category == 'traffic',
                onSelected: (_) => _setCategory('traffic')),
          ]),
        ),
        Expanded(
          child: FutureBuilder<List<dynamic>>(
            future: _future,
            builder: (context, snap) {
              if (snap.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snap.hasError) {
                return Center(
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                    Text('${snap.error}'),
                    const SizedBox(height: 12),
                    FilledButton(onPressed: _reload, child: const Text('Retry')),
                  ]),
                );
              }
              final events = snap.data!.cast<Map<String, dynamic>>();
              if (events.isEmpty) {
                return const Center(child: Text('No events recorded yet'));
              }
              return RefreshIndicator(
                onRefresh: () async {
                  _reload();
                  await _future;
                },
                child: ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: events.length,
                  itemBuilder: (_, i) => _EventCard(event: events[i]),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _EventCard extends StatelessWidget {
  final Map<String, dynamic> event;
  const _EventCard({required this.event});

  @override
  Widget build(BuildContext context) {
    final isCrime = event['category'] == 'crime';
    final desc = event['description'] as String?;
    final confidence = event['confidence'];
    final when = fmtDateTime(parseUtc(event['occurred_at'] as String));

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            CircleAvatar(
              backgroundColor: isCrime ? Colors.red.shade900 : Colors.blue.shade900,
              child: Icon(isCrime ? Icons.warning_amber : Icons.traffic),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(event['event_type'] as String,
                    style: Theme.of(context).textTheme.titleMedium),
                Text('$when · ${event['camera_id']}',
                    style: Theme.of(context).textTheme.bodySmall),
              ]),
            ),
            if (confidence != null) Chip(label: Text('$confidence%')),
          ]),
          if (desc != null && desc.isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 8), child: Text(desc)),
          if (event['has_clip'] == true)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: FilledButton.tonalIcon(
                icon: const Icon(Icons.play_arrow),
                label: const Text('Play Decrypted Clip'),
                onPressed: () => showDialog(
                  context: context,
                  builder: (_) => ClipPlayerDialog(
                    eventId: event['id'] as int,
                    title: event['event_type'] as String,
                  ),
                ),
              ),
            ),
        ]),
      ),
    );
  }
}