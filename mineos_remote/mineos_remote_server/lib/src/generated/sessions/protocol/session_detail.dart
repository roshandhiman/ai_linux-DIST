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
import '../../sessions/protocol/agent_session.dart' as _iwv5bm5e;
import '../../sessions/protocol/agent_step.dart' as _ikdm2o68;

/// A session and the steps revealed so far.
abstract class SessionDetail
    implements _is.SerializableModel, _is.ProtocolSerialization {
  SessionDetail._({
    required this.session,
    required this.steps,
  });

  factory SessionDetail({
    required _iwv5bm5e.AgentSession session,
    required List<_ikdm2o68.AgentStep> steps,
  }) = _SessionDetailImpl;

  factory SessionDetail.fromJson(Map<String, dynamic> jsonSerialization) {
    return SessionDetail(
      session: _ivbyalph.Protocol().deserialize<_iwv5bm5e.AgentSession>(
        jsonSerialization['session'],
      ),
      steps: _ivbyalph.Protocol().deserialize<List<_ikdm2o68.AgentStep>>(
        jsonSerialization['steps'],
      ),
    );
  }

  _iwv5bm5e.AgentSession session;

  List<_ikdm2o68.AgentStep> steps;

  /// Returns a shallow copy of this [SessionDetail]
  /// with some or all fields replaced by the given arguments.
  @_is.useResult
  SessionDetail copyWith({
    _iwv5bm5e.AgentSession? session,
    List<_ikdm2o68.AgentStep>? steps,
  });
  @override
  Map<String, dynamic> toJson() {
    return {
      '__className__': 'SessionDetail',
      'session': session.toJson(),
      'steps': steps.toJson(valueToJson: (v) => v.toJson()),
    };
  }

  @override
  Map<String, dynamic> toJsonForProtocol() {
    return {
      '__className__': 'SessionDetail',
      'session': session.toJsonForProtocol(),
      'steps': steps.toJson(valueToJson: (v) => v.toJsonForProtocol()),
    };
  }

  @override
  String toString() {
    return _is.SerializationManager.encode(this);
  }
}

class _SessionDetailImpl extends SessionDetail {
  _SessionDetailImpl({
    required _iwv5bm5e.AgentSession session,
    required List<_ikdm2o68.AgentStep> steps,
  }) : super._(
         session: session,
         steps: steps,
       );

  /// Returns a shallow copy of this [SessionDetail]
  /// with some or all fields replaced by the given arguments.
  @_is.useResult
  @override
  SessionDetail copyWith({
    _iwv5bm5e.AgentSession? session,
    List<_ikdm2o68.AgentStep>? steps,
  }) {
    return SessionDetail(
      session: session ?? this.session.copyWith(),
      steps: steps ?? this.steps.map((e0) => e0.copyWith()).toList(),
    );
  }
}
