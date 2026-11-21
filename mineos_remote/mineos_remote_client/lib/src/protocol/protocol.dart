/* AUTOMATICALLY GENERATED CODE DO NOT MODIFY */
/*   To generate run: "serverpod generate"    */

// ignore_for_file: implementation_imports
// ignore_for_file: library_private_types_in_public_api
// ignore_for_file: non_constant_identifier_names
// ignore_for_file: public_member_api_docs
// ignore_for_file: type_literal_in_constant_pattern
// ignore_for_file: use_super_parameters
// ignore_for_file: invalid_use_of_internal_member
// ignore_for_file: dead_code, unnecessary_type_check

// ignore_for_file: no_leading_underscores_for_library_prefixes
import 'package:mineos_remote_client/src/protocol/sessions/protocol/agent_session.dart'
    as _ifclqx5t;
import 'package:serverpod_auth_core_client/serverpod_auth_core_client.dart'
    as _iacc;
import 'package:serverpod_auth_idp_client/serverpod_auth_idp_client.dart'
    as _iaic;
import 'package:serverpod_client/serverpod_client.dart' as _isc;
import 'greetings/greeting.dart' as _izw8z7ou;
import 'sessions/protocol/agent_session.dart' as _ily1njrg;
import 'sessions/protocol/agent_step.dart' as _iz8epg7c;
import 'sessions/protocol/replay_event.dart' as _ihiy6y4r;
import 'sessions/protocol/replay_event_type.dart' as _iopknbbc;
import 'sessions/protocol/session_detail.dart' as _i8keovzz;
import 'sessions/protocol/session_not_found_exception.dart' as _i7i6f2iv;
import 'sessions/protocol/session_status.dart' as _i2buyk6g;
import 'sessions/protocol/step_kind.dart' as _iv7b1hh6;
export 'greetings/greeting.dart';
export 'sessions/protocol/agent_session.dart';
export 'sessions/protocol/agent_step.dart';
export 'sessions/protocol/replay_event.dart';
export 'sessions/protocol/replay_event_type.dart';
export 'sessions/protocol/session_detail.dart';
export 'sessions/protocol/session_not_found_exception.dart';
export 'sessions/protocol/session_status.dart';
export 'sessions/protocol/step_kind.dart';
export 'client.dart';

class Protocol extends _isc.SerializationManager
    implements _isc.ProtocolDeserializationProvider {
  Protocol._();

  factory Protocol() => _instance;

  static final Protocol _instance = Protocol._().._registerHostProtocols();

  @override
  _isc.ProtocolDeserialization get deserializationMetadata =>
      _isc.ProtocolDeserialization.cached(
        this,
        types: const [
          _isc.getType<_izw8z7ou.Greeting>,
          _isc.getType<_ily1njrg.AgentSession>,
          _isc.getType<_iz8epg7c.AgentStep>,
          _isc.getType<_ihiy6y4r.ReplayEvent>,
          _isc.getType<_iopknbbc.ReplayEventType>,
          _isc.getType<_i8keovzz.SessionDetail>,
          _isc.getType<_i7i6f2iv.SessionNotFoundException>,
          _isc.getType<_i2buyk6g.SessionStatus>,
          _isc.getType<_iv7b1hh6.StepKind>,
          _isc.getType<_izw8z7ou.Greeting?>,
          _isc.getType<_ily1njrg.AgentSession?>,
          _isc.getType<_iz8epg7c.AgentStep?>,
          _isc.getType<_ihiy6y4r.ReplayEvent?>,
          _isc.getType<_iopknbbc.ReplayEventType?>,
          _isc.getType<_i8keovzz.SessionDetail?>,
          _isc.getType<_i7i6f2iv.SessionNotFoundException?>,
          _isc.getType<_i2buyk6g.SessionStatus?>,
          _isc.getType<_iv7b1hh6.StepKind?>,
          _isc.getType<List<_iz8epg7c.AgentStep>>,
          _isc.getType<List<_iz8epg7c.AgentStep>?>,
          _isc.getType<List<_ifclqx5t.AgentSession>>,
        ],
        modules: const [
          _iaic.Protocol.new,
          _iacc.Protocol.new,
        ],
        classNames: const [
          'Greeting',
          'AgentSession',
          'AgentStep',
          'ReplayEvent',
          'ReplayEventType',
          'SessionDetail',
          'SessionNotFoundException',
          'SessionStatus',
          'StepKind',
        ],
      );

  static String? getClassNameFromObjectJson(dynamic data) =>
      _isc.ProtocolDeserialization.readClassName(data);

  @override
  T deserialize<T>(
    dynamic data, [
    Type? t,
  ]) {
    t ??= T;
    final rawDataClassName = _isc.ProtocolDeserialization.readClassName(data);
    final dataClassName = rawDataClassName;
    if (dataClassName != null && dataClassName != getClassNameForType(t)) {
      try {
        return deserializeByClassName({
          'className': dataClassName,
          'data': data,
        });
      } on _isc.DeserializationClassNameNotFoundException catch (_) {
        // If the className is not recognized (e.g., older client receiving
        // data with a new subtype), fall back to deserializing without the
        // className, using the expected type T.
      }
    }

    if (t == _izw8z7ou.Greeting) {
      return _izw8z7ou.Greeting.fromJson(data) as T;
    }
    if (t == _ily1njrg.AgentSession) {
      return _ily1njrg.AgentSession.fromJson(data) as T;
    }
    if (t == _iz8epg7c.AgentStep) {
      return _iz8epg7c.AgentStep.fromJson(data) as T;
    }
    if (t == _ihiy6y4r.ReplayEvent) {
      return _ihiy6y4r.ReplayEvent.fromJson(data) as T;
    }
    if (t == _iopknbbc.ReplayEventType) {
      return _iopknbbc.ReplayEventType.fromJson(data) as T;
    }
    if (t == _i8keovzz.SessionDetail) {
      return _i8keovzz.SessionDetail.fromJson(data) as T;
    }
    if (t == _i7i6f2iv.SessionNotFoundException) {
      return _i7i6f2iv.SessionNotFoundException.fromJson(data) as T;
    }
    if (t == _i2buyk6g.SessionStatus) {
      return _i2buyk6g.SessionStatus.fromJson(data) as T;
    }
    if (t == _iv7b1hh6.StepKind) {
      return _iv7b1hh6.StepKind.fromJson(data) as T;
    }
    if (t == _isc.getType<_izw8z7ou.Greeting?>()) {
      return (data != null ? _izw8z7ou.Greeting.fromJson(data) : null) as T;
    }
    if (t == _isc.getType<_ily1njrg.AgentSession?>()) {
      return (data != null ? _ily1njrg.AgentSession.fromJson(data) : null) as T;
    }
    if (t == _isc.getType<_iz8epg7c.AgentStep?>()) {
      return (data != null ? _iz8epg7c.AgentStep.fromJson(data) : null) as T;
    }
    if (t == _isc.getType<_ihiy6y4r.ReplayEvent?>()) {
      return (data != null ? _ihiy6y4r.ReplayEvent.fromJson(data) : null) as T;
    }
    if (t == _isc.getType<_iopknbbc.ReplayEventType?>()) {
      return (data != null ? _iopknbbc.ReplayEventType.fromJson(data) : null)
          as T;
    }
    if (t == _isc.getType<_i8keovzz.SessionDetail?>()) {
      return (data != null ? _i8keovzz.SessionDetail.fromJson(data) : null)
          as T;
    }
    if (t == _isc.getType<_i7i6f2iv.SessionNotFoundException?>()) {
      return (data != null
              ? _i7i6f2iv.SessionNotFoundException.fromJson(data)
              : null)
          as T;
    }
    if (t == _isc.getType<_i2buyk6g.SessionStatus?>()) {
      return (data != null ? _i2buyk6g.SessionStatus.fromJson(data) : null)
          as T;
    }
    if (t == _isc.getType<_iv7b1hh6.StepKind?>()) {
      return (data != null ? _iv7b1hh6.StepKind.fromJson(data) : null) as T;
    }
    if (t == List<_iz8epg7c.AgentStep>) {
      return (data as List)
              .map((e) => deserialize<_iz8epg7c.AgentStep>(e))
              .toList()
          as T;
    }
    if (t == _isc.getType<List<_iz8epg7c.AgentStep>?>()) {
      return (data != null
              ? (data as List)
                    .map((e) => deserialize<_iz8epg7c.AgentStep>(e))
                    .toList()
              : null)
          as T;
    }
    if (t == List<_ifclqx5t.AgentSession>) {
      return (data as List)
              .map((e) => deserialize<_ifclqx5t.AgentSession>(e))
              .toList()
          as T;
    }
    final modules = deserializationMetadata.modulesForDeserialization(
      t,
      className: rawDataClassName,
    );
    for (final module in modules) {
      try {
        return module.deserialize<T>(data, t);
      } on _isc.DeserializationTypeNotFoundException catch (_) {}
    }

    return super.deserialize<T>(data, t);
  }

  static String? getClassNameForType(Type type) {
    return switch (type) {
      _izw8z7ou.Greeting => 'Greeting',
      _ily1njrg.AgentSession => 'AgentSession',
      _iz8epg7c.AgentStep => 'AgentStep',
      _ihiy6y4r.ReplayEvent => 'ReplayEvent',
      _iopknbbc.ReplayEventType => 'ReplayEventType',
      _i8keovzz.SessionDetail => 'SessionDetail',
      _i7i6f2iv.SessionNotFoundException => 'SessionNotFoundException',
      _i2buyk6g.SessionStatus => 'SessionStatus',
      _iv7b1hh6.StepKind => 'StepKind',
      _ => null,
    };
  }

  @override
  String? getClassNameForObject(Object? data) {
    String? className = super.getClassNameForObject(data);
    if (className != null) return className;

    if (data is Map<String, dynamic> && data['__className__'] is String) {
      return (data['__className__'] as String).replaceFirst(
        'mineos_remote.',
        '',
      );
    }

    switch (data) {
      case _izw8z7ou.Greeting():
        return 'Greeting';
      case _ily1njrg.AgentSession():
        return 'AgentSession';
      case _iz8epg7c.AgentStep():
        return 'AgentStep';
      case _ihiy6y4r.ReplayEvent():
        return 'ReplayEvent';
      case _iopknbbc.ReplayEventType():
        return 'ReplayEventType';
      case _i8keovzz.SessionDetail():
        return 'SessionDetail';
      case _i7i6f2iv.SessionNotFoundException():
        return 'SessionNotFoundException';
      case _i2buyk6g.SessionStatus():
        return 'SessionStatus';
      case _iv7b1hh6.StepKind():
        return 'StepKind';
    }
    className = _iaic.Protocol().getClassNameForObject(data);
    if (className != null) {
      return className.contains('.')
          ? className
          : 'serverpod_auth_idp.$className';
    }
    className = _iacc.Protocol().getClassNameForObject(data);
    if (className != null) {
      return className.contains('.')
          ? className
          : 'serverpod_auth_core.$className';
    }
    return null;
  }

  @override
  dynamic deserializeByClassName(Map<String, dynamic> data) {
    var dataClassName = data['className'];
    if (dataClassName is! String) {
      return super.deserializeByClassName(data);
    }
    if (dataClassName == 'Greeting') {
      return deserialize<_izw8z7ou.Greeting>(data['data']);
    }
    if (dataClassName == 'AgentSession') {
      return deserialize<_ily1njrg.AgentSession>(data['data']);
    }
    if (dataClassName == 'AgentStep') {
      return deserialize<_iz8epg7c.AgentStep>(data['data']);
    }
    if (dataClassName == 'ReplayEvent') {
      return deserialize<_ihiy6y4r.ReplayEvent>(data['data']);
    }
    if (dataClassName == 'ReplayEventType') {
      return deserialize<_iopknbbc.ReplayEventType>(data['data']);
    }
    if (dataClassName == 'SessionDetail') {
      return deserialize<_i8keovzz.SessionDetail>(data['data']);
    }
    if (dataClassName == 'SessionNotFoundException') {
      return deserialize<_i7i6f2iv.SessionNotFoundException>(data['data']);
    }
    if (dataClassName == 'SessionStatus') {
      return deserialize<_i2buyk6g.SessionStatus>(data['data']);
    }
    if (dataClassName == 'StepKind') {
      return deserialize<_iv7b1hh6.StepKind>(data['data']);
    }
    if (dataClassName.startsWith('serverpod_auth_idp.')) {
      return _iaic.Protocol().deserializeByClassName({
        ...data,
        'className': dataClassName.substring(19),
      });
    }
    if (dataClassName.startsWith('serverpod_auth_core.')) {
      return _iacc.Protocol().deserializeByClassName({
        ...data,
        'className': dataClassName.substring(20),
      });
    }
    return super.deserializeByClassName(data);
  }

  void _registerHostProtocols() {
    _iaic.Protocol().registerHostProtocol('mineos_remote', this);
    _iacc.Protocol().registerHostProtocol('mineos_remote', this);
  }

  @override
  String getModuleName() => 'mineos_remote';

  /// Maps any `Record`s known to this [Protocol] to their JSON representation
  ///
  /// Throws in case the record type is not known.
  ///
  /// This method will return `null` (only) for `null` inputs.
  Map<String, dynamic>? mapRecordToJson(Record? record) {
    if (record == null) {
      return null;
    }
    try {
      return _iaic.Protocol().mapRecordToJson(record);
    } catch (_) {}
    try {
      return _iacc.Protocol().mapRecordToJson(record);
    } catch (_) {}
    throw Exception('Unsupported record type ${record.runtimeType}');
  }
}
