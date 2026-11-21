/* AUTOMATICALLY GENERATED CODE DO NOT MODIFY */
/*   To generate run: "serverpod generate"    */

// ignore_for_file: implementation_imports
// ignore_for_file: library_private_types_in_public_api
// ignore_for_file: non_constant_identifier_names
// ignore_for_file: public_member_api_docs
// ignore_for_file: type_literal_in_constant_pattern
// ignore_for_file: use_super_parameters
// ignore_for_file: invalid_use_of_internal_member

// ignore_for_file: no_leading_underscores_for_library_prefixes
import 'package:serverpod_client/serverpod_client.dart' as _isc;
import '../../sessions/protocol/step_kind.dart' as _ieq6bcjp;

/// One step of a recorded agent session.
abstract class AgentStep
    implements _isc.SerializableModel, _isc.ProtocolSerialization {
  AgentStep._({
    this.id,
    required this.sessionId,
    required this.index,
    required this.kind,
    required this.title,
    required this.detail,
    required this.durationMs,
    required this.createdAt,
  });

  factory AgentStep({
    int? id,
    required int sessionId,
    required int index,
    required _ieq6bcjp.StepKind kind,
    required String title,
    required String detail,
    required int durationMs,
    required DateTime createdAt,
  }) = _AgentStepImpl;

  factory AgentStep.fromJson(Map<String, dynamic> jsonSerialization) {
    return AgentStep(
      id: jsonSerialization['id'] as int?,
      sessionId: jsonSerialization['sessionId'] as int,
      index: jsonSerialization['index'] as int,
      kind: _ieq6bcjp.StepKind.fromJson((jsonSerialization['kind'] as String)),
      title: jsonSerialization['title'] as String,
      detail: jsonSerialization['detail'] as String,
      durationMs: jsonSerialization['durationMs'] as int,
      createdAt: _isc.DateTimeJsonExtension.fromJson(
        jsonSerialization['createdAt'],
      ),
    );
  }

  /// The database id, set if the object has been inserted into the
  /// database or if it has been fetched from the database. Otherwise,
  /// the id will be null.
  int? id;

  int sessionId;

  /// 1-based position in the session.
  int index;

  _ieq6bcjp.StepKind kind;

  String title;

  /// The trace text, shown in a monospace font.
  String detail;

  int durationMs;

  DateTime createdAt;

  /// Returns a shallow copy of this [AgentStep]
  /// with some or all fields replaced by the given arguments.
  @_isc.useResult
  AgentStep copyWith({
    int? id,
    int? sessionId,
    int? index,
    _ieq6bcjp.StepKind? kind,
    String? title,
    String? detail,
    int? durationMs,
    DateTime? createdAt,
  });
  @override
  Map<String, dynamic> toJson() {
    return {
      '__className__': 'AgentStep',
      if (id != null) 'id': id,
      'sessionId': sessionId,
      'index': index,
      'kind': kind.toJson(),
      'title': title,
      'detail': detail,
      'durationMs': durationMs,
      'createdAt': createdAt.toJson(),
    };
  }

  @override
  Map<String, dynamic> toJsonForProtocol() {
    return {
      '__className__': 'AgentStep',
      if (id != null) 'id': id,
      'sessionId': sessionId,
      'index': index,
      'kind': kind.toJson(),
      'title': title,
      'detail': detail,
      'durationMs': durationMs,
      'createdAt': createdAt.toJson(),
    };
  }

  @override
  String toString() {
    return _isc.SerializationManager.encode(this);
  }
}

class _Undefined {}

class _AgentStepImpl extends AgentStep {
  _AgentStepImpl({
    int? id,
    required int sessionId,
    required int index,
    required _ieq6bcjp.StepKind kind,
    required String title,
    required String detail,
    required int durationMs,
    required DateTime createdAt,
  }) : super._(
         id: id,
         sessionId: sessionId,
         index: index,
         kind: kind,
         title: title,
         detail: detail,
         durationMs: durationMs,
         createdAt: createdAt,
       );

  /// Returns a shallow copy of this [AgentStep]
  /// with some or all fields replaced by the given arguments.
  @_isc.useResult
  @override
  AgentStep copyWith({
    Object? id = _Undefined,
    int? sessionId,
    int? index,
    _ieq6bcjp.StepKind? kind,
    String? title,
    String? detail,
    int? durationMs,
    DateTime? createdAt,
  }) {
    return AgentStep(
      id: id is int? ? id : this.id,
      sessionId: sessionId ?? this.sessionId,
      index: index ?? this.index,
      kind: kind ?? this.kind,
      title: title ?? this.title,
      detail: detail ?? this.detail,
      durationMs: durationMs ?? this.durationMs,
      createdAt: createdAt ?? this.createdAt,
    );
  }
}
