import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'config.dart';

class ApiException implements Exception {
  final int status;
  final String message;
  ApiException(this.status, this.message);
  @override
  String toString() => message;
}

class ApiClient {
  ApiClient._();
  static final ApiClient instance = ApiClient._();

  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  final ValueNotifier<bool> authState = ValueNotifier<bool>(false);
  String? _access;
  String? _refresh;

  Future<void> loadSession() async {
    _access = await _storage.read(key: 'access_token');
    _refresh = await _storage.read(key: 'refresh_token');
    authState.value = _refresh != null;
  }

  Future<void> _saveTokens(Map<String, dynamic> json) async {
    _access = json['access_token'] as String;
    _refresh = json['refresh_token'] as String;
    await _storage.write(key: 'access_token', value: _access);
    await _storage.write(key: 'refresh_token', value: _refresh);
    authState.value = true;
  }

  Future<void> logout() async {
    _access = null;
    _refresh = null;
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
    authState.value = false;
  }

  String _detail(http.Response r) {
    try {
      final d = jsonDecode(r.body)['detail'];
      if (d is String) return d;
    } catch (_) {}
    return 'Request failed (${r.statusCode})';
  }

  Future<void> login(String username, String password) async {
    final r = await http.post(
      Uri.parse('$apiBase/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'password': password}),
    );
    if (r.statusCode != 200) throw ApiException(r.statusCode, _detail(r));
    await _saveTokens(jsonDecode(r.body) as Map<String, dynamic>);
  }

  Future<bool> _refreshTokens() async {
    if (_refresh == null) return false;
    try {
      final r = await http.post(
        Uri.parse('$apiBase/auth/refresh'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh_token': _refresh}),
      );
      if (r.statusCode != 200) return false;
      await _saveTokens(jsonDecode(r.body) as Map<String, dynamic>);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<dynamic> _getJson(String path, {Map<String, String>? query}) async {
    final uri = Uri.parse('$apiBase$path').replace(queryParameters: query);
    Future<http.Response> send() =>
        http.get(uri, headers: {'Authorization': 'Bearer $_access'});

    var r = await send();
    if (r.statusCode == 401 && await _refreshTokens()) r = await send();
    if (r.statusCode == 401) {
      await logout();
      throw ApiException(401, 'Session expired, please log in again');
    }
    if (r.statusCode >= 400) throw ApiException(r.statusCode, _detail(r));
    return jsonDecode(r.body);
  }

  Future<Map<String, dynamic>> dashboard() async =>
      (await _getJson('/dashboard')) as Map<String, dynamic>;

  Future<List<dynamic>> events({String? category}) async => (await _getJson(
        '/events',
        query: category == null ? null : {'category': category},
      )) as List<dynamic>;

  Future<Map<String, dynamic>> analytics({String? date}) async =>
      (await _getJson('/analytics', query: date == null ? null : {'date': date}))
          as Map<String, dynamic>;

  /// Returns a full URL with a short-lived token the video player can open directly.
  Future<String> clipUrl(int eventId) async {
    final j = (await _getJson('/events/$eventId/clip-token')) as Map<String, dynamic>;
    final path = j['url'] as String;
    return '$apiBase$path';
  }
}