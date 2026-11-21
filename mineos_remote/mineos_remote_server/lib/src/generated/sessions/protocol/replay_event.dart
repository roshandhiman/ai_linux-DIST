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
import 'package:mineos_remote_server/src/generated/protocol.dart' as _ivbyalph;
import 'package:serverpod/serverpod.dart' as _is;
import '../../sessions/protocol/agent_step.dart' as _ikdm2o68;
import '../../sessions/protocol/replay_event_type.dart' as _im5x2qfi;

/// One event of a session replay.
abstract class ReplayEvent
    implements _is.SerializableModel, _is.ProtocolSerialization {
  ReplayEvent._({
    required this.type,
    required this.cycle,
    this.step,
    this.label,
    this.startedAt,
  });

  factory ReplayEvent({
    required _im5x2qfi.ReplayEventType type,
    required int cycle,
    _ikdm2o68.AgentStep? step,
    String? label,
    DateTime? startedAt,
  }) = _ReplayEventImpl;

  factory ReplayEvent.fromJson(Map<String, dynamic> jsonSerialization) {
    return ReplayEvent(
      type: _im5x2qfi.ReplayEventType.fromJson(
        (jsonSerialization['type'] as String),
      ),
      cycle: jsonSerialization['cycle'] as int,
      step: jsonSerialization['step'] == null
          ? null
          : _ivbyalph.Protocol().deserialize<_ikdm2o68.AgentStep>(
              jsonSerialization['step'],
            ),
      label: jsonSerialization['label'] as String?,
      startedAt: jsonSerialization['startedAt'] == null
          ? null
          : _is.DateTimeJsonExtension.fromJson(jsonSerialization['startedAt']),
    );
  }

  _im5x2qfi.ReplayEventType type;

  /// Which loop of a running session this belongs to.
  int cycle;

  _ikdm2o68.AgentStep? step;

  String? label;

  /// When the current loop started (running sessions only).
  DateTime? startedAt;

  /// Returns a shallow copy of this [ReplayEvent]
  /// with some or all fields replaced by the given arguments.
  @_is.useResult
  ReplayEvent copyWith({
    _im5x2qfi.ReplayEventType? type,
    int? cycle,
    _ikdm2o68.AgentStep? step = const _UndefinedReplayEvent$step(),
    String? label,
    DateTime? startedAt = const _is.$UndefinedDateTime(),
  });
  @override
  Map<String, dynamic> toJson() {
    return {
      '__className__': 'ReplayEvent',
      'type': type.toJson(),
      'cycle': cycle,
      if (step != null) 'step': step?.toJson(),
      if (label != null) 'label': label,
      if (startedAt != null) 'startedAt': startedAt?.toJson(),
    };
  }

  @override
  Map<String, dynamic> toJsonForProtocol() {
    return {
      '__className__': 'ReplayEvent',
      'type': type.toJson(),
      'cycle': cycle,
      if (step != null) 'step': step?.toJsonForProtocol(),
      if (label != null) 'label': label,
      if (startedAt != null) 'startedAt': startedAt?.toJson(),
    };
  }

  @override
  String toString() {
    return _is.SerializationManager.encode(this);
  }
}

class _Undefined {}

class _UndefinedReplayEvent$step extends _is.UndefinedSentinel
    implements _ikdm2o68.AgentStep {
  const _UndefinedReplayEvent$step();
}

class _ReplayEventImpl extends ReplayEvent {
  _ReplayEventImpl({
    required _im5x2qfi.ReplayEventType type,
    required int cycle,
    _ikdm2o68.AgentStep? step,
    String? label,
    DateTime? startedAt,
  }) : super._(
         type: type,
         cycle: cycle,
         step: step,
         label: label,
         startedAt: startedAt,
       );

  /// Returns a shallow copy of this [ReplayEvent]
  /// with some or all fields replaced by the given arguments.
  @_is.useResult
  @override
  ReplayEvent copyWith({
    _im5x2qfi.ReplayEventType? type,
    int? cycle,
    _ikdm2o68.AgentStep? step = const _UndefinedReplayEvent$step(),
    Object? label = _Undefined,
    DateTime? startedAt = const _is.$UndefinedDateTime(),
  }) {
    return ReplayEvent(
      type: type ?? this.type,
      cycle: cycle ?? this.cycle,
      step: step is _is.UndefinedSentinel ? this.step?.copyWith() : step,
      label: label is String? ? label : this.label,
      startedAt: startedAt is _is.UndefinedSentinel
          ? this.startedAt
          : startedAt,
    );
  }
}
