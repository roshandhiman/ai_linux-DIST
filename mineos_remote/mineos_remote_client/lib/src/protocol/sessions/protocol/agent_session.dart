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
import 'package:mineos_remote_client/src/protocol/protocol.dart' as _it7fk1u1;
import 'package:serverpod_client/serverpod_client.dart' as _isc;
import '../../sessions/protocol/agent_step.dart' as _ikdm2o68;
import '../../sessions/protocol/session_status.dart' as _ipzmcjjz;

/// One recorded MineOS agent session (one turn of the terminal agent).
abstract class AgentSession
    implements _isc.SerializableModel, _isc.ProtocolSerialization {
  AgentSession._({
    this.id,
    required this.task,
    required this.status,
    required this.modelName,
    required this.provider,
    required this.isLocal,
    required this.route,
    this.outcome,
    this.answer,
    required this.startedAt,
    required this.updatedAt,
    required this.stepCount,
    this.steps,
  });

  factory AgentSession({
    int? id,
    required String task,
    required _ipzmcjjz.SessionStatus status,
    required String modelName,
    required String provider,
    required bool isLocal,
    required String route,
    String? outcome,
    String? answer,
    required DateTime startedAt,
    required DateTime updatedAt,
    required int stepCount,
    List<_ikdm2o68.AgentStep>? steps,
  }) = _AgentSessionImpl;

  factory AgentSession.fromJson(Map<String, dynamic> jsonSerialization) {
    return AgentSession(
      id: jsonSerialization['id'] as int?,
      task: jsonSerialization['task'] as String,
      status: _ipzmcjjz.SessionStatus.fromJson(
        (jsonSerialization['status'] as String),
      ),
      modelName: jsonSerialization['modelName'] as String,
      provider: jsonSerialization['provider'] as String,
      isLocal: _isc.BoolJsonExtension.fromJson(jsonSerialization['isLocal']),
      route: jsonSerialization['route'] as String,
      outcome: jsonSerialization['outcome'] as String?,
      answer: jsonSerialization['answer'] as String?,
      startedAt: _isc.DateTimeJsonExtension.fromJson(
        jsonSerialization['startedAt'],
      ),
      updatedAt: _isc.DateTimeJsonExtension.fromJson(
        jsonSerialization['updatedAt'],
      ),
      stepCount: jsonSerialization['stepCount'] as int,
      steps: jsonSerialization['steps'] == null
          ? null
          : _it7fk1u1.Protocol().deserialize<List<_ikdm2o68.AgentStep>>(
              jsonSerialization['steps'],
            ),
    );
  }

  /// The database id, set if the object has been inserted into the
  /// database or if it has been fetched from the database. Otherwise,
  /// the id will be null.
  int? id;

  /// The user's request, as typed.
  String task;

  _ipzmcjjz.SessionStatus status;

  /// The model as the agent logs it, e.g. qwen2.5-1.5b-instruct.
  String modelName;

  /// Where the model ran, e.g. "local".
  String provider;

  /// True when the model ran on the machine and no data left it.
  bool isLocal;

  /// The router's decision: "INTENT confidence via backend".
  String route;

  /// The turn's outcome when it ended: answered, stuck, declined...
  String? outcome;

  String? answer;

  DateTime startedAt;

  DateTime updatedAt;

  int stepCount;

  List<_ikdm2o68.AgentStep>? steps;

  /// Returns a shallow copy of this [AgentSession]
  /// with some or all fields replaced by the given arguments.
  @_isc.useResult
  AgentSession copyWith({
    int? id,
    String? task,
    _ipzmcjjz.SessionStatus? status,
    String? modelName,
    String? provider,
    bool? isLocal,
    String? route,
    String? outcome,
    String? answer,
    DateTime? startedAt,
    DateTime? updatedAt,
    int? stepCount,
    List<_ikdm2o68.AgentStep>? steps =
        const _isc.$UndefinedList<_ikdm2o68.AgentStep>(),
  });
  @override
  Map<String, dynamic> toJson() {
    return {
      '__className__': 'AgentSession',
      if (id != null) 'id': id,
      'task': task,
      'status': status.toJson(),
      'modelName': modelName,
      'provider': provider,
      'isLocal': isLocal,
      'route': route,
      if (outcome != null) 'outcome': outcome,
      if (answer != null) 'answer': answer,
      'startedAt': startedAt.toJson(),
      'updatedAt': updatedAt.toJson(),
      'stepCount': stepCount,
      if (steps != null) 'steps': steps?.toJson(valueToJson: (v) => v.toJson()),
    };
  }

  @override
  Map<String, dynamic> toJsonForProtocol() {
    return {
      '__className__': 'AgentSession',
      if (id != null) 'id': id,
      'task': task,
      'status': status.toJson(),
      'modelName': modelName,
      'provider': provider,
      'isLocal': isLocal,
      'route': route,
      if (outcome != null) 'outcome': outcome,
      if (answer != null) 'answer': answer,
      'startedAt': startedAt.toJson(),
      'updatedAt': updatedAt.toJson(),
      'stepCount': stepCount,
      if (steps != null)
        'steps': steps?.toJson(valueToJson: (v) => v.toJsonForProtocol()),
    };
  }

  @override
  String toString() {
    return _isc.SerializationManager.encode(this);
  }
}

class _Undefined {}

class _AgentSessionImpl extends AgentSession {
  _AgentSessionImpl({
    int? id,
    required String task,
    required _ipzmcjjz.SessionStatus status,
    required String modelName,
    required String provider,
    required bool isLocal,
    required String route,
    String? outcome,
    String? answer,
    required DateTime startedAt,
    required DateTime updatedAt,
    required int stepCount,
    List<_ikdm2o68.AgentStep>? steps,
  }) : super._(
         id: id,
         task: task,
         status: status,
         modelName: modelName,
         provider: provider,
         isLocal: isLocal,
         route: route,
         outcome: outcome,
         answer: answer,
         startedAt: startedAt,
         updatedAt: updatedAt,
         stepCount: stepCount,
         steps: steps,
       );

  /// Returns a shallow copy of this [AgentSession]
  /// with some or all fields replaced by the given arguments.
  @_isc.useResult
  @override
  AgentSession copyWith({
    Object? id = _Undefined,
    String? task,
    _ipzmcjjz.SessionStatus? status,
    String? modelName,
    String? provider,
    bool? isLocal,
    String? route,
    Object? outcome = _Undefined,
    Object? answer = _Undefined,
    DateTime? startedAt,
    DateTime? updatedAt,
    int? stepCount,
    List<_ikdm2o68.AgentStep>? steps =
        const _isc.$UndefinedList<_ikdm2o68.AgentStep>(),
  }) {
    return AgentSession(
      id: id is int? ? id : this.id,
      task: task ?? this.task,
      status: status ?? this.status,
      modelName: modelName ?? this.modelName,
      provider: provider ?? this.provider,
      isLocal: isLocal ?? this.isLocal,
      route: route ?? this.route,
      outcome: outcome is String? ? outcome : this.outcome,
      answer: answer is String? ? answer : this.answer,
      startedAt: startedAt ?? this.startedAt,
      updatedAt: updatedAt ?? this.updatedAt,
      stepCount: stepCount ?? this.stepCount,
      steps: steps is _isc.UndefinedSentinel
          ? this.steps?.map((e0) => e0.copyWith()).toList()
          : steps,
    );
  }
}
