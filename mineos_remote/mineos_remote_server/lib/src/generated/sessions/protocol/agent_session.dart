/* AUTOMATICALLY GENERATED CODE DO NOT MODIFY */
/*   To generate run: "serverpod generate"    */

// ignore_for_file: implementation_imports
// ignore_for_file: library_private_types_in_public_api
// ignore_for_file: non_constant_identifier_names
// ignore_for_file: public_member_api_docs
// ignore_for_file: type_literal_in_constant_pattern
// ignore_for_file: use_super_parameters
// ignore_for_file: invalid_use_of_internal_member
// ignore_for_file: dead_code, unnecessary_null_comparison

// ignore_for_file: no_leading_underscores_for_library_prefixes
import 'dart:async' as _ida;
import 'package:mineos_remote_server/src/generated/protocol.dart' as _ivbyalph;
import 'package:serverpod/serverpod.dart' as _is;
import '../../sessions/protocol/agent_step.dart' as _ikdm2o68;
import '../../sessions/protocol/session_status.dart' as _ipzmcjjz;

/// One recorded MineOS agent session (one turn of the terminal agent).
abstract class AgentSession
    implements _is.TableRow<int?>, _is.ProtocolSerialization {
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
      isLocal: _is.BoolJsonExtension.fromJson(jsonSerialization['isLocal']),
      route: jsonSerialization['route'] as String,
      outcome: jsonSerialization['outcome'] as String?,
      answer: jsonSerialization['answer'] as String?,
      startedAt: _is.DateTimeJsonExtension.fromJson(
        jsonSerialization['startedAt'],
      ),
      updatedAt: _is.DateTimeJsonExtension.fromJson(
        jsonSerialization['updatedAt'],
      ),
      stepCount: jsonSerialization['stepCount'] as int,
      steps: jsonSerialization['steps'] == null
          ? null
          : _ivbyalph.Protocol().deserialize<List<_ikdm2o68.AgentStep>>(
              jsonSerialization['steps'],
            ),
    );
  }

  static final t = AgentSessionTable();

  static const db = AgentSessionRepository._();

  @override
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

  @override
  _is.Table<int?> get table => t;

  /// Returns a shallow copy of this [AgentSession]
  /// with some or all fields replaced by the given arguments.
  @_is.useResult
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
        const _is.$UndefinedList<_ikdm2o68.AgentStep>(),
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

  static AgentSessionInclude include({_ikdm2o68.AgentStepIncludeList? steps}) {
    return AgentSessionInclude._(steps: steps);
  }

  static AgentSessionIncludeList includeList({
    _is.WhereExpressionBuilder<AgentSessionTable>? where,
    int? limit,
    int? offset,
    _is.OrderByBuilder<AgentSessionTable>? orderBy,
    _is.OrderByListBuilder<AgentSessionTable>? orderByList,
    AgentSessionInclude? include,
  }) {
    return AgentSessionIncludeList._(
      where: where,
      limit: limit,
      offset: offset,
      orderBy: orderBy?.call(AgentSession.t),
      orderByList: orderByList?.call(AgentSession.t),
      include: include,
    );
  }

  @override
  String toString() {
    return _is.SerializationManager.encode(this);
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
  @_is.useResult
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
        const _is.$UndefinedList<_ikdm2o68.AgentStep>(),
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
      steps: steps is _is.UndefinedSentinel
          ? this.steps?.map((e0) => e0.copyWith()).toList()
          : steps,
    );
  }
}

class AgentSessionUpdateTable extends _is.UpdateTable<AgentSessionTable> {
  AgentSessionUpdateTable(super.table);

  _is.ColumnValue<String, String> task(String value) => _is.ColumnValue(
    table.task,
    value,
  );

  _is.ColumnValue<_ipzmcjjz.SessionStatus, _ipzmcjjz.SessionStatus> status(
    _ipzmcjjz.SessionStatus value,
  ) => _is.ColumnValue(
    table.status,
    value,
  );

  _is.ColumnValue<String, String> modelName(String value) => _is.ColumnValue(
    table.modelName,
    value,
  );

  _is.ColumnValue<String, String> provider(String value) => _is.ColumnValue(
    table.provider,
    value,
  );

  _is.ColumnValue<bool, bool> isLocal(bool value) => _is.ColumnValue(
    table.isLocal,
    value,
  );

  _is.ColumnValue<String, String> route(String value) => _is.ColumnValue(
    table.route,
    value,
  );

  _is.ColumnValue<String, String> outcome(String? value) => _is.ColumnValue(
    table.outcome,
    value,
  );

  _is.ColumnValue<String, String> answer(String? value) => _is.ColumnValue(
    table.answer,
    value,
  );

  _is.ColumnValue<DateTime, DateTime> startedAt(DateTime value) =>
      _is.ColumnValue(
        table.startedAt,
        value,
      );

  _is.ColumnValue<DateTime, DateTime> updatedAt(DateTime value) =>
      _is.ColumnValue(
        table.updatedAt,
        value,
      );

  _is.ColumnValue<int, int> stepCount(int value) => _is.ColumnValue(
    table.stepCount,
    value,
  );
}

class AgentSessionTable extends _is.Table<int?> {
  AgentSessionTable({super.tableRelation}) : super(tableName: 'agent_session') {
    updateTable = AgentSessionUpdateTable(this);
    task = _is.ColumnString(
      'task',
      this,
    );
    status = _is.ColumnEnum(
      'status',
      this,
      _is.EnumSerialization.byName,
    );
    modelName = _is.ColumnString(
      'modelName',
      this,
    );
    provider = _is.ColumnString(
      'provider',
      this,
    );
    isLocal = _is.ColumnBool(
      'isLocal',
      this,
    );
    route = _is.ColumnString(
      'route',
      this,
    );
    outcome = _is.ColumnString(
      'outcome',
      this,
    );
    answer = _is.ColumnString(
      'answer',
      this,
    );
    startedAt = _is.ColumnDateTime(
      'startedAt',
      this,
    );
    updatedAt = _is.ColumnDateTime(
      'updatedAt',
      this,
    );
    stepCount = _is.ColumnInt(
      'stepCount',
      this,
    );
  }

  late final AgentSessionUpdateTable updateTable;

  /// The user's request, as typed.
  late final _is.ColumnString task;

  late final _is.ColumnEnum<_ipzmcjjz.SessionStatus> status;

  /// The model as the agent logs it, e.g. qwen2.5-1.5b-instruct.
  late final _is.ColumnString modelName;

  /// Where the model ran, e.g. "local".
  late final _is.ColumnString provider;

  /// True when the model ran on the machine and no data left it.
  late final _is.ColumnBool isLocal;

  /// The router's decision: "INTENT confidence via backend".
  late final _is.ColumnString route;

  /// The turn's outcome when it ended: answered, stuck, declined...
  late final _is.ColumnString outcome;

  late final _is.ColumnString answer;

  late final _is.ColumnDateTime startedAt;

  late final _is.ColumnDateTime updatedAt;

  late final _is.ColumnInt stepCount;

  _ikdm2o68.AgentStepTable? ___steps;

  _is.ManyRelation<_ikdm2o68.AgentStepTable>? _steps;

  _ikdm2o68.AgentStepTable get __steps {
    if (___steps != null) return ___steps!;
    ___steps = _is.createRelationTable(
      relationFieldName: '__steps',
      field: AgentSession.t.id,
      foreignField: _ikdm2o68.AgentStep.t.sessionId,
      tableRelation: tableRelation,
      createTable: (foreignTableRelation) =>
          _ikdm2o68.AgentStepTable(tableRelation: foreignTableRelation),
    );
    return ___steps!;
  }

  _is.ManyRelation<_ikdm2o68.AgentStepTable> get steps {
    if (_steps != null) return _steps!;
    var relationTable = _is.createRelationTable(
      relationFieldName: 'steps',
      field: AgentSession.t.id,
      foreignField: _ikdm2o68.AgentStep.t.sessionId,
      tableRelation: tableRelation,
      createTable: (foreignTableRelation) =>
          _ikdm2o68.AgentStepTable(tableRelation: foreignTableRelation),
    );
    _steps = _is.ManyRelation<_ikdm2o68.AgentStepTable>(
      tableWithRelations: relationTable,
      table: _ikdm2o68.AgentStepTable(
        tableRelation: relationTable.tableRelation!.lastRelation,
      ),
    );
    return _steps!;
  }

  @override
  List<_is.Column> get columns => [
    id,
    task,
    status,
    modelName,
    provider,
    isLocal,
    route,
    outcome,
    answer,
    startedAt,
    updatedAt,
    stepCount,
  ];

  @override
  _is.Table? getRelationTable(String relationField) {
    if (relationField == 'steps') {
      return __steps;
    }
    return null;
  }
}

class AgentSessionInclude extends _is.IncludeObject {
  AgentSessionInclude._({_ikdm2o68.AgentStepIncludeList? steps}) {
    _steps = steps;
  }

  _ikdm2o68.AgentStepIncludeList? _steps;

  @override
  Map<String, _is.Include?> get includes => {'steps': _steps};

  @override
  _is.Table<int?> get table => AgentSession.t;
}

class AgentSessionIncludeList extends _is.IncludeList {
  AgentSessionIncludeList._({
    _is.WhereExpressionBuilder<AgentSessionTable>? where,
    super.limit,
    super.offset,
    super.orderBy,
    super.orderByList,
    super.include,
  }) {
    super.where = where?.call(AgentSession.t);
  }

  @override
  Map<String, _is.Include?> get includes => include?.includes ?? {};

  @override
  _is.Table<int?> get table => AgentSession.t;
}

class AgentSessionRepository {
  const AgentSessionRepository._();

  final attach = const AgentSessionAttachRepository._();

  final attachRow = const AgentSessionAttachRowRepository._();

  /// Returns a list of [AgentSession]s matching the given query parameters.
  ///
  /// Use [where] to specify which items to include in the return value.
  /// If none is specified, all items will be returned.
  ///
  /// To specify the order of the items use [orderBy] or [orderByList]
  /// when sorting by multiple columns.
  ///
  /// The maximum number of items can be set by [limit]. If no limit is set,
  /// all items matching the query will be returned.
  ///
  /// [offset] defines how many items to skip, after which [limit] (or all)
  /// items are read from the database.
  ///
  /// ```dart
  /// var persons = await Persons.db.find(
  ///   session,
  ///   where: (t) => t.lastName.equals('Jones'),
  ///   orderBy: (t) => t.firstName,
  ///   limit: 100,
  /// );
  /// ```
  Future<List<AgentSession>> find(
    _is.DatabaseSession session, {
    _is.WhereExpressionBuilder<AgentSessionTable>? where,
    int? limit,
    int? offset,
    _is.OrderByBuilder<AgentSessionTable>? orderBy,
    _is.OrderByListBuilder<AgentSessionTable>? orderByList,
    _is.Transaction? transaction,
    AgentSessionInclude? include,
    _is.LockMode? lockMode,
    _is.LockBehavior? lockBehavior,
  }) async {
    return session.db.find<AgentSession>(
      where: where?.call(AgentSession.t),
      orderBy: orderBy?.call(AgentSession.t),
      orderByList: orderByList?.call(AgentSession.t),
      limit: limit,
      offset: offset,
      transaction: transaction,
      include: include,
      lockMode: lockMode,
      lockBehavior: lockBehavior,
    );
  }

  /// Emits [AgentSession]s matching the given query parameters every time the
  /// source tables are modified.
  ///
  /// Use [where] to specify which items to include in the return value.
  /// If none is specified, all items will be returned.
  ///
  /// To specify the order of the items use [orderBy] or [orderByList]
  /// when sorting by multiple columns.
  ///
  /// The maximum number of items can be set by [limit]. If no limit is set,
  /// all items matching the query will be returned.
  ///
  /// [offset] defines how many items to skip, after which [limit] (or all)
  /// items are read from the database.
  ///
  /// Use [throttle] to specify the minimum interval between queries. It can
  /// also be set to `null`, in which case the stream will only be throttled
  /// when its subscription is paused.
  ///
  /// Source tables are collected from the queried table, [where], [orderBy],
  /// [orderByList], and the [include] graph. [alsoTriggerOnTables] is added
  /// to that set. Pass [Table] instances such as `AgentSession.t`.
  ///
  /// Raw [Expression] SQL is not inspected. Tables referenced only in raw
  /// SQL must be passed via [alsoTriggerOnTables].
  ///
  /// The stream always reads committed state and never joins an ambient
  /// [Transaction]. Emissions for a write fire after that write commits.
  ///
  /// Currently only supported on SQLite. Calling this method on PostgreSQL
  /// throws an [UnsupportedError].
  ///
  /// ```dart
  /// var subscription = Persons.db.watch(
  ///   session,
  ///   where: (t) => t.lastName.equals('Jones'),
  ///   orderBy: (t) => t.firstName,
  ///   limit: 100,
  /// ).listen((persons) {
  ///   // Handle the latest matching rows.
  /// });
  /// ```
  _ida.Stream<List<AgentSession>> watch(
    _is.DatabaseSession session, {
    _is.WhereExpressionBuilder<AgentSessionTable>? where,
    int? limit,
    int? offset,
    _is.OrderByBuilder<AgentSessionTable>? orderBy,
    _is.OrderByListBuilder<AgentSessionTable>? orderByList,
    AgentSessionInclude? include,
    Duration? throttle = const Duration(milliseconds: 30),
    Iterable<_is.Table>? alsoTriggerOnTables,
  }) {
    return session.db.watch<AgentSession>(
      where: where?.call(AgentSession.t),
      orderBy: orderBy?.call(AgentSession.t),
      orderByList: orderByList?.call(AgentSession.t),
      limit: limit,
      offset: offset,
      include: include,
      throttle: throttle,
      alsoTriggerOnTables: alsoTriggerOnTables,
    );
  }

  /// Returns the first matching [AgentSession] matching the given query parameters.
  ///
  /// Use [where] to specify which items to include in the return value.
  /// If none is specified, all items will be returned.
  ///
  /// To specify the order use [orderBy] or [orderByList]
  /// when sorting by multiple columns.
  ///
  /// [offset] defines how many items to skip, after which the next one will be picked.
  ///
  /// ```dart
  /// var youngestPerson = await Persons.db.findFirstRow(
  ///   session,
  ///   where: (t) => t.lastName.equals('Jones'),
  ///   orderBy: (t) => t.age,
  /// );
  /// ```
  Future<AgentSession?> findFirstRow(
    _is.DatabaseSession session, {
    _is.WhereExpressionBuilder<AgentSessionTable>? where,
    int? offset,
    _is.OrderByBuilder<AgentSessionTable>? orderBy,
    _is.OrderByListBuilder<AgentSessionTable>? orderByList,
    _is.Transaction? transaction,
    AgentSessionInclude? include,
    _is.LockMode? lockMode,
    _is.LockBehavior? lockBehavior,
  }) async {
    return session.db.findFirstRow<AgentSession>(
      where: where?.call(AgentSession.t),
      orderBy: orderBy?.call(AgentSession.t),
      orderByList: orderByList?.call(AgentSession.t),
      offset: offset,
      transaction: transaction,
      include: include,
      lockMode: lockMode,
      lockBehavior: lockBehavior,
    );
  }

  /// Finds a single [AgentSession] by its [id] or null if no such row exists.
  Future<AgentSession?> findById(
    _is.DatabaseSession session,
    int id, {
    _is.Transaction? transaction,
    AgentSessionInclude? include,
    _is.LockMode? lockMode,
    _is.LockBehavior? lockBehavior,
  }) async {
    return session.db.findById<AgentSession>(
      id,
      transaction: transaction,
      include: include,
      lockMode: lockMode,
      lockBehavior: lockBehavior,
    );
  }

  /// Inserts all [AgentSession]s in the list and returns the inserted rows.
  ///
  /// The returned [AgentSession]s will have their `id` fields set.
  ///
  /// This is an atomic operation, meaning that if one of the rows fails to
  /// insert, none of the rows will be inserted.
  ///
  /// If [ignoreConflicts] is set to `true`, rows that conflict with existing
  /// rows are silently skipped, and only the successfully inserted rows are
  /// returned.
  ///
  /// If [noReturn] is set to `true`, the inserted rows are not read back from
  /// the database and an empty list is returned. This avoids the overhead of
  /// transferring and deserializing the rows when the result is not needed.
  Future<List<AgentSession>> insert(
    _is.DatabaseSession session,
    List<AgentSession> rows, {
    _is.Transaction? transaction,
    bool ignoreConflicts = false,
    bool noReturn = false,
  }) async {
    return session.db.insert<AgentSession>(
      rows,
      transaction: transaction,
      ignoreConflicts: ignoreConflicts,
      noReturn: noReturn,
    );
  }

  /// Inserts a single [AgentSession] and returns the inserted row.
  ///
  /// The returned [AgentSession] will have its `id` field set.
  Future<AgentSession> insertRow(
    _is.DatabaseSession session,
    AgentSession row, {
    _is.Transaction? transaction,
  }) async {
    return session.db.insertRow<AgentSession>(
      row,
      transaction: transaction,
    );
  }

  /// Upserts all [AgentSession]s in the list and returns the resulting rows.
  ///
  /// If a row conflicts on the given [conflictColumns], the existing row is
  /// updated with the new values. Otherwise, a new row is inserted.
  ///
  /// If [updateColumns] is provided, only those columns will be updated on
  /// conflict. If null, all non-conflict, non-id columns are updated.
  ///
  /// If [updateWhere] is provided, the update only applies to rows matching the
  /// given expression. Conflicting rows that don't match are skipped and not
  /// returned, so the resulting list may be shorter than [rows].
  ///
  /// The returned [AgentSession]s will have their `id` fields set.
  ///
  /// This is an atomic operation, meaning that if one of the rows fails,
  /// none of the rows will be affected.
  ///
  /// If [noReturn] is set to `true`, the resulting rows are not read back from
  /// the database and an empty list is returned. This avoids the overhead of
  /// transferring and deserializing the rows when the result is not needed.
  Future<List<AgentSession>> upsert(
    _is.DatabaseSession session,
    List<AgentSession> rows, {
    required _is.ColumnSelections<AgentSessionTable> conflictColumns,
    _is.ColumnSelections<AgentSessionTable>? updateColumns,
    _is.WhereExpressionBuilder<AgentSessionTable>? updateWhere,
    _is.Transaction? transaction,
    bool noReturn = false,
  }) async {
    return session.db.upsert<AgentSession>(
      rows,
      conflictColumns: conflictColumns(AgentSession.t),
      updateColumns: updateColumns?.call(AgentSession.t),
      updateWhere: updateWhere?.call(AgentSession.t),
      transaction: transaction,
      noReturn: noReturn,
    );
  }

  /// Upserts a single [AgentSession] and returns the resulting row.
  ///
  /// If the row conflicts on the given [conflictColumns], the existing row is
  /// updated. Otherwise, a new row is inserted.
  ///
  /// If [updateColumns] is provided, only those columns will be updated on
  /// conflict. If null, all non-conflict, non-id columns are updated.
  ///
  /// If [updateWhere] is provided, the update only applies when the existing
  /// row matches the expression. Returns `null` if no row was affected — for
  /// example when [updateWhere] does not match the conflicting row.
  ///
  /// The returned [AgentSession] will have its `id` field set.
  Future<AgentSession?> upsertRow(
    _is.DatabaseSession session,
    AgentSession row, {
    required _is.ColumnSelections<AgentSessionTable> conflictColumns,
    _is.ColumnSelections<AgentSessionTable>? updateColumns,
    _is.WhereExpressionBuilder<AgentSessionTable>? updateWhere,
    _is.Transaction? transaction,
  }) async {
    return session.db.upsertRow<AgentSession>(
      row,
      conflictColumns: conflictColumns(AgentSession.t),
      updateColumns: updateColumns?.call(AgentSession.t),
      updateWhere: updateWhere?.call(AgentSession.t),
      transaction: transaction,
    );
  }

  /// Updates all [AgentSession]s in the list and returns the updated rows. If
  /// [columns] is provided, only those columns will be updated. Defaults to
  /// all columns.
  /// This is an atomic operation, meaning that if one of the rows fails to
  /// update, none of the rows will be updated.
  ///
  /// If [noReturn] is set to `true`, the updated rows are not read back from
  /// the database and an empty list is returned. This avoids the overhead of
  /// transferring and deserializing the rows when the result is not needed.
  Future<List<AgentSession>> update(
    _is.DatabaseSession session,
    List<AgentSession> rows, {
    _is.ColumnSelections<AgentSessionTable>? columns,
    _is.Transaction? transaction,
    bool noReturn = false,
  }) async {
    return session.db.update<AgentSession>(
      rows,
      columns: columns?.call(AgentSession.t),
      transaction: transaction,
      noReturn: noReturn,
    );
  }

  /// Updates a single [AgentSession]. The row needs to have its id set.
  /// Optionally, a list of [columns] can be provided to only update those
  /// columns. Defaults to all columns.
  Future<AgentSession> updateRow(
    _is.DatabaseSession session,
    AgentSession row, {
    _is.ColumnSelections<AgentSessionTable>? columns,
    _is.Transaction? transaction,
  }) async {
    return session.db.updateRow<AgentSession>(
      row,
      columns: columns?.call(AgentSession.t),
      transaction: transaction,
    );
  }

  /// Updates a single [AgentSession] by its [id] with the specified [columnValues].
  /// Returns the updated row or null if no row with the given id exists.
  Future<AgentSession?> updateById(
    _is.DatabaseSession session,
    int id, {
    required _is.ColumnValueListBuilder<AgentSessionUpdateTable> columnValues,
    _is.Transaction? transaction,
  }) async {
    return session.db.updateById<AgentSession>(
      id,
      columnValues: columnValues(AgentSession.t.updateTable),
      transaction: transaction,
    );
  }

  /// Updates all [AgentSession]s matching the [where] expression with the specified [columnValues].
  /// Returns the list of updated rows.
  ///
  /// If [noReturn] is set to `true`, the updated rows are not read back from
  /// the database and an empty list is returned. This avoids the overhead of
  /// transferring and deserializing the rows when the result is not needed.
  Future<List<AgentSession>> updateWhere(
    _is.DatabaseSession session, {
    required _is.ColumnValueListBuilder<AgentSessionUpdateTable> columnValues,
    required _is.WhereExpressionBuilder<AgentSessionTable> where,
    int? limit,
    int? offset,
    _is.OrderByBuilder<AgentSessionTable>? orderBy,
    _is.OrderByListBuilder<AgentSessionTable>? orderByList,
    _is.Transaction? transaction,
    bool noReturn = false,
  }) async {
    return session.db.updateWhere<AgentSession>(
      columnValues: columnValues(AgentSession.t.updateTable),
      where: where(AgentSession.t),
      limit: limit,
      offset: offset,
      orderBy: orderBy?.call(AgentSession.t),
      orderByList: orderByList?.call(AgentSession.t),
      transaction: transaction,
      noReturn: noReturn,
    );
  }

  /// Deletes all [AgentSession]s in the list and returns the deleted rows.
  ///
  /// To specify the order of the returned rows use [orderBy] or [orderByList]
  /// when sorting by multiple columns.
  ///
  /// This is an atomic operation, meaning that if one of the rows fail to
  /// be deleted, none of the rows will be deleted.
  ///
  /// If [noReturn] is set to `true`, the deleted rows are not read back from
  /// the database and an empty list is returned. This avoids the overhead of
  /// transferring and deserializing the rows when the result is not needed.
  Future<List<AgentSession>> delete(
    _is.DatabaseSession session,
    List<AgentSession> rows, {
    _is.OrderByBuilder<AgentSessionTable>? orderBy,
    _is.OrderByListBuilder<AgentSessionTable>? orderByList,
    _is.Transaction? transaction,
    bool noReturn = false,
  }) async {
    return session.db.delete<AgentSession>(
      rows,
      orderBy: orderBy?.call(AgentSession.t),
      orderByList: orderByList?.call(AgentSession.t),
      transaction: transaction,
      noReturn: noReturn,
    );
  }

  /// Deletes a single [AgentSession].
  Future<AgentSession> deleteRow(
    _is.DatabaseSession session,
    AgentSession row, {
    _is.Transaction? transaction,
  }) async {
    return session.db.deleteRow<AgentSession>(
      row,
      transaction: transaction,
    );
  }

  /// Deletes all rows matching the [where] expression.
  ///
  /// To specify the order of the returned rows use [orderBy] or [orderByList]
  /// when sorting by multiple columns.
  ///
  /// If [noReturn] is set to `true`, the deleted rows are not read back from
  /// the database and an empty list is returned. This avoids the overhead of
  /// transferring and deserializing the rows when the result is not needed.
  Future<List<AgentSession>> deleteWhere(
    _is.DatabaseSession session, {
    required _is.WhereExpressionBuilder<AgentSessionTable> where,
    _is.OrderByBuilder<AgentSessionTable>? orderBy,
    _is.OrderByListBuilder<AgentSessionTable>? orderByList,
    _is.Transaction? transaction,
    bool noReturn = false,
  }) async {
    return session.db.deleteWhere<AgentSession>(
      where: where(AgentSession.t),
      orderBy: orderBy?.call(AgentSession.t),
      orderByList: orderByList?.call(AgentSession.t),
      transaction: transaction,
      noReturn: noReturn,
    );
  }

  /// Counts the number of rows matching the [where] expression. If omitted,
  /// will return the count of all rows in the table.
  Future<int> count(
    _is.DatabaseSession session, {
    _is.WhereExpressionBuilder<AgentSessionTable>? where,
    int? limit,
    _is.Transaction? transaction,
  }) async {
    return session.db.count<AgentSession>(
      where: where?.call(AgentSession.t),
      limit: limit,
      transaction: transaction,
    );
  }

  /// Acquires row-level locks on [AgentSession] rows matching the [where] expression.
  Future<void> lockRows(
    _is.DatabaseSession session, {
    required _is.WhereExpressionBuilder<AgentSessionTable> where,
    required _is.LockMode lockMode,
    required _is.Transaction transaction,
    _is.LockBehavior lockBehavior = _is.LockBehavior.wait,
  }) async {
    return session.db.lockRows<AgentSession>(
      where: where(AgentSession.t),
      lockMode: lockMode,
      lockBehavior: lockBehavior,
      transaction: transaction,
    );
  }
}

class AgentSessionAttachRepository {
  const AgentSessionAttachRepository._();

  /// Creates a relation between this [AgentSession] and the given [AgentStep]s
  /// by setting each [AgentStep]'s foreign key `sessionId` to refer to this [AgentSession].
  Future<void> steps(
    _is.DatabaseSession session,
    AgentSession agentSession,
    List<_ikdm2o68.AgentStep> agentStep, {
    _is.Transaction? transaction,
  }) async {
    if (agentStep.any((e) => e.id == null)) {
      throw ArgumentError.notNull('agentStep.id');
    }
    if (agentSession.id == null) {
      throw ArgumentError.notNull('agentSession.id');
    }

    var $agentStep = agentStep
        .map((e) => e.copyWith(sessionId: agentSession.id))
        .toList();
    await session.db.update<_ikdm2o68.AgentStep>(
      $agentStep,
      columns: [_ikdm2o68.AgentStep.t.sessionId],
      transaction: transaction,
    );
  }
}

class AgentSessionAttachRowRepository {
  const AgentSessionAttachRowRepository._();

  /// Creates a relation between this [AgentSession] and the given [AgentStep]
  /// by setting the [AgentStep]'s foreign key `sessionId` to refer to this [AgentSession].
  Future<void> steps(
    _is.DatabaseSession session,
    AgentSession agentSession,
    _ikdm2o68.AgentStep agentStep, {
    _is.Transaction? transaction,
  }) async {
    if (agentStep.id == null) {
      throw ArgumentError.notNull('agentStep.id');
    }
    if (agentSession.id == null) {
      throw ArgumentError.notNull('agentSession.id');
    }

    var $agentStep = agentStep.copyWith(sessionId: agentSession.id);
    await session.db.updateRow<_ikdm2o68.AgentStep>(
      $agentStep,
      columns: [_ikdm2o68.AgentStep.t.sessionId],
      transaction: transaction,
    );
  }
}
