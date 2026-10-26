import 'package:flutter/material.dart';

import '../api_client.dart';
import 'analytics_screen.dart';
import 'dashboard_screen.dart';
import 'events_screen.dart';
import 'live_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  static const _titles = ['Dashboard', 'Live Feed', 'Evidence Log', 'Analytics'];

  // Pages are rebuilt on tab change on purpose, so the Live page closes its
  // WebRTC connection when you leave it.
  Widget _page() {
    switch (_index) {
      case 0:
        return DashboardScreen(onOpenLive: () => setState(() => _index = 1));
      case 1:
        return const LiveScreen();
      case 2:
        return const EventsScreen();
      default:
        return const AnalyticsScreen();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_titles[_index]),
        actions: [
          IconButton(
            tooltip: 'Log out',
            icon: const Icon(Icons.logout),
            onPressed: () => ApiClient.instance.logout(),
          ),
        ],
      ),
      body: _page(),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard_outlined), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.videocam_outlined), label: 'Live'),
          NavigationDestination(icon: Icon(Icons.folder_open), label: 'Evidence'),
          NavigationDestination(icon: Icon(Icons.bar_chart), label: 'Analytics'),
        ],
      ),
    );
  }
}