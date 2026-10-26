/// Backend timestamps are naive UTC strings; treat them as UTC, show local time.
DateTime parseUtc(String s) {
  final hasZone = s.endsWith('Z') || RegExp(r'[+-]\d\d:\d\d$').hasMatch(s);
  return DateTime.parse(hasZone ? s : '${s}Z').toLocal();
}

String _two(int n) => n.toString().padLeft(2, '0');

String fmtDateTime(DateTime d) =>
    '${d.year}-${_two(d.month)}-${_two(d.day)} ${_two(d.hour)}:${_two(d.minute)}';