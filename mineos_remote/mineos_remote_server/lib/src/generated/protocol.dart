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
import 'package:mineos_remote_server/src/generated/sessions/protocol/agent_session.dart'
    as _izegx9o3;
import 'package:serverpod/protocol.dart' as _isp;
import 'package:serverpod/serverpod.dart' as _is;
import 'package:serverpod_auth_core_server/serverpod_auth_core_server.dart'
    as _iacs;
import 'package:serverpod_auth_idp_server/serverpod_auth_idp_server.dart'
    as _iais;
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

class Protocol extends _is.DatabaseSerializationManager
    implements _is.DatabaseProtocolDeserializationProvider {
  Protocol._();

  factory Protocol() => _instance;

  static final Protocol _instance = Protocol._().._registerHostProtocols();

  @override
  _is.ProtocolDeserialization get deserializationMetadata =>
      _is.ProtocolDeserialization.cached(
        this,
        types: const [
          _is.getType<_izw8z7ou.Greeting>,
          _is.getType<_ily1njrg.AgentSession>,
          _is.getType<_iz8epg7c.AgentStep>,
          _is.getType<_ihiy6y4r.ReplayEvent>,
          _is.getType<_iopknbbc.ReplayEventType>,
          _is.getType<_i8keovzz.SessionDetail>,
          _is.getType<_i7i6f2iv.SessionNotFoundException>,
          _is.getType<_i2buyk6g.SessionStatus>,
          _is.getType<_iv7b1hh6.StepKind>,
          _is.getType<_izw8z7ou.Greeting?>,
          _is.getType<_ily1njrg.AgentSession?>,
          _is.getType<_iz8epg7c.AgentStep?>,
          _is.getType<_ihiy6y4r.ReplayEvent?>,
          _is.getType<_iopknbbc.ReplayEventType?>,
          _is.getType<_i8keovzz.SessionDetail?>,
          _is.getType<_i7i6f2iv.SessionNotFoundException?>,
          _is.getType<_i2buyk6g.SessionStatus?>,
          _is.getType<_iv7b1hh6.StepKind?>,
          _is.getType<List<_iz8epg7c.AgentStep>>,
          _is.getType<List<_iz8epg7c.AgentStep>?>,
          _is.getType<List<_izegx9o3.AgentSession>>,
        ],
        modules: const [
          _iais.Protocol.new,
          _iacs.Protocol.new,
          _isp.Protocol.new,
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

  static List<_isp.TableDefinition> get targetTableDefinitions => [
    ..._ownTableDefinitions,
    ..._iais.Protocol().getOwnTableDefinitions(),
    ..._iacs.Protocol().getOwnTableDefinitions(),
    ..._isp.Protocol.targetTableDefinitions,
  ];

  static List<_isp.TableDefinition> get _ownTableDefinitions => [
    _isp.TableDefinition(
      name: 'agent_session',
      dartName: 'AgentSession',
      schema: 'public',
      module: 'mineos_remote',
      columns: [
        _isp.ColumnDefinition(
          name: 'id',
          columnType: _isp.ColumnType.bigint,
          isNullable: false,
          dartType: 'int?',
          columnDefault: 'serial',
        ),
        _isp.ColumnDefinition(
          name: 'task',
          columnType: _isp.ColumnType.text,
          isNullable: false,
          dartType: 'String',
        ),
        _isp.ColumnDefinition(
          name: 'status',
          columnType: _isp.ColumnType.text,
          isNullable: false,
          dartType: 'protocol:SessionStatus',
        ),
        _isp.ColumnDefinition(
          name: 'modelName',
          columnType: _isp.ColumnType.text,
          isNullable: false,
          dartType: 'String',
        ),
        _isp.ColumnDefinition(
          name: 'provider',
          columnType: _isp.ColumnType.text,
          isNullable: false,
          dartType: 'String',
        ),
        _isp.ColumnDefinition(
          name: 'isLocal',
          columnType: _isp.ColumnType.boolean,
          isNullable: false,
          dartType: 'bool',
        ),
        _isp.ColumnDefinition(
          name: 'route',
          columnType: _isp.ColumnType.text,
          isNullable: false,
          dartType: 'String',
        ),
        _isp.ColumnDefinition(
          name: 'outcome',
          columnType: _isp.ColumnType.text,
          isNullable: true,
          dartType: 'String?',
        ),
        _isp.ColumnDefinition(
          name: 'answer',
          columnType: _isp.ColumnType.text,
          isNullable: true,
          dartType: 'String?',
        ),
        _isp.ColumnDefinition(
          name: 'startedAt',
          columnType: _isp.ColumnType.timestampWithoutTimeZone,
          isNullable: false,
          dartType: 'DateTime',
        ),
        _isp.ColumnDefinition(
          name: 'updatedAt',
          columnType: _isp.ColumnType.timestampWithoutTimeZone,
          isNullable: false,
          dartType: 'DateTime',
        ),
        _isp.ColumnDefinition(
          name: 'stepCount',
          columnType: _isp.ColumnType.bigint,
          isNullable: false,
          dartType: 'int',
        ),
      ],
      foreignKeys: [],
      indexes: [
        _isp.IndexDefinition(
          indexName: 'agent_session_started_idx',
          tableSpace: null,
          elements: [
            _isp.IndexElementDefinition(
              type: _isp.IndexElementDefinitionType.column,
              definition: 'startedAt',
            ),
          ],
          type: 'btree',
          isUnique: false,
          isPrimary: false,
        ),
      ],
      managed: true,
    ),
    _isp.TableDefinition(
      name: 'agent_step',
      dartName: 'AgentStep',
      schema: 'public',
      module: 'mineos_remote',
      columns: [
        _isp.ColumnDefinition(
          name: 'id',
          columnType: _isp.ColumnType.bigint,
          isNullable: false,
          dartType: 'int?',
          columnDefault: 'serial',
        ),
        _isp.ColumnDefinition(
          name: 'sessionId',
          columnType: _isp.ColumnType.bigint,
          isNullable: false,
          dartType: 'int',
        ),
        _isp.ColumnDefinition(
          name: 'index',
          columnType: _isp.ColumnType.bigint,
          isNullable: false,
          dartType: 'int',
        ),
        _isp.ColumnDefinition(
          name: 'kind',
          columnType: _isp.ColumnType.text,
          isNullable: false,
          dartType: 'protocol:StepKind',
        ),
        _isp.ColumnDefinition(
          name: 'title',
          columnType: _isp.ColumnType.text,
          isNullable: false,
          dartType: 'String',
        ),
        _isp.ColumnDefinition(
          name: 'detail',
          columnType: _isp.ColumnType.text,
          isNullable: false,
          dartType: 'String',
        ),
        _isp.ColumnDefinition(
          name: 'durationMs',
          columnType: _isp.ColumnType.bigint,
          isNullable: false,
          dartType: 'int',
        ),
        _isp.ColumnDefinition(
          name: 'createdAt',
          columnType: _isp.ColumnType.timestampWithoutTimeZone,
          isNullable: false,
          dartType: 'DateTime',
        ),
      ],
      foreignKeys: [
        _isp.ForeignKeyDefinition(
          constraintName: 'agent_step_fk_0',
          columns: ['sessionId'],
          referenceTable: 'agent_session',
          referenceTableSchema: 'public',
          referenceColumns: ['id'],
          onUpdate: _isp.ForeignKeyAction.noAction,
          onDelete: _isp.ForeignKeyAction.noAction,
          matchType: null,
        ),
      ],
      indexes: [
        _isp.IndexDefinition(
          indexName: 'agent_step_session_index_idx',
          tableSpace: null,
          elements: [
            _isp.IndexElementDefinition(
              type: _isp.IndexElementDefinitionType.column,
              definition: 'sessionId',
            ),
            _isp.IndexElementDefinition(
              type: _isp.IndexElementDefinitionType.column,
              definition: 'index',
            ),
          ],
          type: 'btree',
          isUnique: true,
          isPrimary: false,
        ),
      ],
      managed: true,
    ),
  ];

  static String? getClassNameFromObjectJson(dynamic data) =>
      _is.ProtocolDeserialization.readClassName(data);

  @override
  T deserialize<T>(
    dynamic data, [
    Type? t,
  ]) {
    t ??= T;
    final rawDataClassName = _is.ProtocolDeserialization.readClassName(data);
    final dataClassName = rawDataClassName;
    if (dataClassName != null && dataClassName != getClassNameForType(t)) {
      try {
        return deserializeByClassName({
          'className': dataClassName,
          'data': data,
        });
      } on _is.DeserializationClassNameNotFoundException catch (_) {
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
    if (t == _is.getType<_izw8z7ou.Greeting?>()) {
      return (data != null ? _izw8z7ou.Greeting.fromJson(data) : null) as T;
    }
    if (t == _is.getType<_ily1njrg.AgentSession?>()) {
      return (data != null ? _ily1njrg.AgentSession.fromJson(data) : null) as T;
    }
    if (t == _is.getType<_iz8epg7c.AgentStep?>()) {
      return (data != null ? _iz8epg7c.AgentStep.fromJson(data) : null) as T;
    }
    if (t == _is.getType<_ihiy6y4r.ReplayEvent?>()) {
      return (data != null ? _ihiy6y4r.ReplayEvent.fromJson(data) : null) as T;
    }
    if (t == _is.getType<_iopknbbc.ReplayEventType?>()) {
      return (data != null ? _iopknbbc.ReplayEventType.fromJson(data) : null)
          as T;
    }
    if (t == _is.getType<_i8keovzz.SessionDetail?>()) {
      return (data != null ? _i8keovzz.SessionDetail.fromJson(data) : null)
          as T;
    }
    if (t == _is.getType<_i7i6f2iv.SessionNotFoundException?>()) {
      return (data != null
              ? _i7i6f2iv.SessionNotFoundException.fromJson(data)
              : null)
          as T;
    }
    if (t == _is.getType<_i2buyk6g.SessionStatus?>()) {
      return (data != null ? _i2buyk6g.SessionStatus.fromJson(data) : null)
          as T;
    }
    if (t == _is.getType<_iv7b1hh6.StepKind?>()) {
      return (data != null ? _iv7b1hh6.StepKind.fromJson(data) : null) as T;
    }
    if (t == List<_iz8epg7c.AgentStep>) {
      return (data as List)
              .map((e) => deserialize<_iz8epg7c.AgentStep>(e))
              .toList()
          as T;
    }
    if (t == _is.getType<List<_iz8epg7c.AgentStep>?>()) {
      return (data != null
              ? (data as List)
                    .map((e) => deserialize<_iz8epg7c.AgentStep>(e))
                    .toList()
              : null)
          as T;
    }
    if (t == List<_izegx9o3.AgentSession>) {
      return (data as List)
              .map((e) => deserialize<_izegx9o3.AgentSession>(e))
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
      } on _is.DeserializationTypeNotFoundException catch (_) {}
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
    className = _iais.Protocol().getClassNameForObject(data);
    if (className != null) {
      return className.contains('.')
          ? className
          : 'serverpod_auth_idp.$className';
    }
    className = _iacs.Protocol().getClassNameForObject(data);
    if (className != null) {
      return className.contains('.')
          ? className
          : 'serverpod_auth_core.$className';
    }
    className = _isp.Protocol().getClassNameForObject(data);
    if (className != null) {
      return className.contains('.') ? className : 'serverpod.$className';
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
      return _iais.Protocol().deserializeByClassName({
        ...data,
        'className': dataClassName.substring(19),
      });
    }
    if (dataClassName.startsWith('serverpod_auth_core.')) {
      return _iacs.Protocol().deserializeByClassName({
        ...data,
        'className': dataClassName.substring(20),
      });
    }
    if (dataClassName.startsWith('serverpod.')) {
      return _isp.Protocol().deserializeByClassName({
        ...data,
        'className': dataClassName.substring(10),
      });
    }
    return super.deserializeByClassName(data);
  }

  void _registerHostProtocols() {
    _iais.Protocol().registerHostProtocol('mineos_remote', this);
    _iacs.Protocol().registerHostProtocol('mineos_remote', this);
  }

  @override
  _is.Table? getTableForType(Type t) {
    {
      var table = _iais.Protocol().getTableForType(t);
      if (table != null) {
        return table;
      }
    }
    {
      var table = _iacs.Protocol().getTableForType(t);
      if (table != null) {
        return table;
      }
    }
    {
      var table = _isp.Protocol().getTableForType(t);
      if (table != null) {
        return table;
      }
    }
    switch (t) {
      case _ily1njrg.AgentSession:
        return _ily1njrg.AgentSession.t;
      case _iz8epg7c.AgentStep:
        return _iz8epg7c.AgentStep.t;
    }
    return null;
  }

  @override
  List<_isp.TableDefinition> getTargetTableDefinitions() =>
      targetTableDefinitions;

  @override
  List<_isp.TableDefinition> getOwnTableDefinitions() => _ownTableDefinitions;

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
      return _iais.Protocol().mapRecordToJson(record);
    } catch (_) {}
    try {
      return _iacs.Protocol().mapRecordToJson(record);
    } catch (_) {}
    throw Exception('Unsupported record type ${record.runtimeType}');
  }
}
