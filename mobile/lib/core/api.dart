import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Backend manzili: flutter run --dart-define=API_URL=https://api.example.uz
/// Android emulyatorda localhost -> 10.0.2.2
const String apiUrl = String.fromEnvironment('API_URL', defaultValue: 'https://imkon-market.uz');

class ApiException implements Exception {
  final int status;
  final dynamic data;
  ApiException(this.status, this.data);

  String get message {
    final d = data;
    if (d is Map) {
      if (d['detail'] != null) return d['detail'].toString();
      return d.entries.map((e) => '${e.key}: ${e.value is List ? (e.value as List).join(', ') : e.value}').join('; ');
    }
    return d?.toString() ?? 'Error $status';
  }

  @override
  String toString() => message;
}

class Api {
  Api._();
  static final Api i = Api._();

  String? _access;
  String? _refresh;

  bool get authed => _access != null;

  Future<void> loadTokens() async {
    final p = await SharedPreferences.getInstance();
    _access = p.getString('access');
    _refresh = p.getString('refresh');
  }

  Future<void> setTokens(String access, [String? refresh]) async {
    _access = access;
    if (refresh != null) _refresh = refresh;
    final p = await SharedPreferences.getInstance();
    await p.setString('access', access);
    if (refresh != null) await p.setString('refresh', refresh);
  }

  Future<void> clearTokens() async {
    _access = null;
    _refresh = null;
    final p = await SharedPreferences.getInstance();
    await p.remove('access');
    await p.remove('refresh');
  }

  Uri uri(String path, [Map<String, dynamic>? query]) {
    final q = <String, String>{};
    query?.forEach((k, v) {
      if (v != null && v.toString().isNotEmpty && v != false) q[k] = v.toString();
    });
    return Uri.parse('$apiUrl/api$path').replace(queryParameters: q.isEmpty ? null : q);
  }

  Future<dynamic> get(String path, {Map<String, dynamic>? query, bool auth = false}) =>
      _send('GET', path, query: query, auth: auth);

  Future<dynamic> post(String path, {Object? body, bool auth = false}) => _send('POST', path, body: body, auth: auth);

  Future<dynamic> patch(String path, {Object? body, bool auth = false}) => _send('PATCH', path, body: body, auth: auth);

  Future<dynamic> _send(String method, String path,
      {Map<String, dynamic>? query, Object? body, bool auth = false, bool retry = true}) async {
    final headers = <String, String>{'Accept': 'application/json'};
    if (body != null) headers['Content-Type'] = 'application/json';
    if (auth && _access != null) headers['Authorization'] = 'Bearer $_access';
    final req = http.Request(method, uri(path, query))..headers.addAll(headers);
    if (body != null) req.body = jsonEncode(body);
    final res = await http.Response.fromStream(await req.send().timeout(const Duration(seconds: 30)));
    if (res.statusCode == 401 && auth && retry && await _refreshToken()) {
      return _send(method, path, query: query, body: body, auth: auth, retry: false);
    }
    final text = utf8.decode(res.bodyBytes);
    dynamic data;
    try {
      data = text.isEmpty ? null : jsonDecode(text);
    } catch (_) {
      data = text;
    }
    if (res.statusCode >= 400) throw ApiException(res.statusCode, data);
    return data;
  }

  Future<bool> _refreshToken() async {
    if (_refresh == null) return false;
    final res = await http.post(uri('/auth/refresh/'),
        headers: {'Content-Type': 'application/json'}, body: jsonEncode({'refresh': _refresh}));
    if (res.statusCode != 200) return false;
    await setTokens(jsonDecode(res.body)['access'] as String);
    return true;
  }
}
