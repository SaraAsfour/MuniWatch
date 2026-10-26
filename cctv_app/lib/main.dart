import 'package:flutter/material.dart';

import 'api_client.dart';
import 'screens/home_shell.dart';
import 'screens/login_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const CctvApp());
}

class CctvApp extends StatefulWidget {
  const CctvApp({super.key});
  @override
  State<CctvApp> createState() => _CctvAppState();
}

class _CctvAppState extends State<CctvApp> {
  late final Future<void> _init = ApiClient.instance.loadSession();

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI CCTV Monitor',
      debugShowCheckedModeBanner: false,
      themeMode: ThemeMode.dark,
      darkTheme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.indigo,
          brightness: Brightness.dark,
        ),
      ),
      home: FutureBuilder<void>(
        future: _init,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Scaffold(body: Center(child: CircularProgressIndicator()));
          }
          return ValueListenableBuilder<bool>(
            valueListenable: ApiClient.instance.authState,
            builder: (_, loggedIn, __) =>
                loggedIn ? const HomeShell() : const LoginScreen(),
          );
        },
      ),
    );
  }
}