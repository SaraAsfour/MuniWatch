import 'dart:math';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../api_client.dart';

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({super.key});
  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  DateTime _date = DateTime.now();
  late Future<Map<String, dynamic>> _future = _fetch();

  Future<Map<String, dynamic>> _fetch() =>
      ApiClient.instance.analytics(date: _date.toIso8601String().substring(0, 10));

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2024),
      lastDate: DateTime.now(),
    );
    if (picked != null) {
      setState(() {
        _date = picked;
        _future = _fetch();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snap.hasError) {
          return Center(child: Text('${snap.error}'));
        }
        final data = snap.data!;
        final flow = (data['hourly_flow'] as List).cast<Map<String, dynamic>>();
        final counts = flow.map((p) => p['vehicle_count'] as int).toList();
        final maxCount = counts.isEmpty ? 0 : counts.reduce(max);
        final peak = data['peak_hour'] as int;
        final totalIncidents = data['total_incidents'] as int;
        final scheme = Theme.of(context).colorScheme;

        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Row(children: [
              Text(data['date'] as String,
                  style: Theme.of(context).textTheme.titleMedium),
              const Spacer(),
              OutlinedButton.icon(
                onPressed: _pickDate,
                icon: const Icon(Icons.calendar_today, size: 18),
                label: const Text('Change date'),
              ),
            ]),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(maxCount > 0 ? '${peak.toString().padLeft(2, '0')}:00' : '—',
                          style: Theme.of(context).textTheme.headlineMedium),
                      Text('Peak hour', style: Theme.of(context).textTheme.bodySmall),
                    ]),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('$totalIncidents',
                          style: Theme.of(context).textTheme.headlineMedium),
                      Text('Total events', style: Theme.of(context).textTheme.bodySmall),
                    ]),
                  ),
                ),
              ),
            ]),
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 16, 16, 12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Padding(
                    padding: const EdgeInsets.only(left: 4, bottom: 12),
                    child: Text('Hourly flow rate',
                        style: Theme.of(context).textTheme.titleMedium),
                  ),
                  SizedBox(
                    height: 260,
                    child: BarChart(
                      BarChartData(
                        alignment: BarChartAlignment.spaceAround,
                        maxY: max(1, maxCount) * 1.2,
                        gridData: const FlGridData(show: true, drawVerticalLine: false),
                        borderData: FlBorderData(show: false),
                        titlesData: FlTitlesData(
                          topTitles: const AxisTitles(
                              sideTitles: SideTitles(showTitles: false)),
                          rightTitles: const AxisTitles(
                              sideTitles: SideTitles(showTitles: false)),
                          leftTitles: const AxisTitles(
                              sideTitles: SideTitles(showTitles: true, reservedSize: 32)),
                          bottomTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              reservedSize: 28,
                              getTitlesWidget: (value, meta) {
                                final h = value.toInt();
                                return Padding(
                                  padding: const EdgeInsets.only(top: 6),
                                  child: Text(h % 3 == 0 ? '${h}h' : '',
                                      style: const TextStyle(fontSize: 11)),
                                );
                              },
                            ),
                          ),
                        ),
                        barGroups: [
                          for (final p in flow)
                            BarChartGroupData(x: p['hour'] as int, barRods: [
                              BarChartRodData(
                                toY: (p['vehicle_count'] as int).toDouble(),
                                width: 8,
                                borderRadius: BorderRadius.circular(2),
                                color: (maxCount > 0 && p['hour'] == peak)
                                    ? Colors.orangeAccent
                                    : scheme.primary,
                              ),
                            ]),
                        ],
                      ),
                    ),
                  ),
                ]),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Use the peak hours (highlighted) to decide when to allocate more resources to the monitored area.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        );
      },
    );
  }
}