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
import 'dart:async' as _ida;
import 'package:serverpod/serverpod.dart' as _is;
import '../../sessions/protocol/step_kind.dart' as _ieq6bcjp;

/// One step of a recorded agent session.
abstract class AgentStep
    implements _is.TableRow<int?>, _is.ProtocolSerialization {
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
      createdAt: _is.DateTimeJsonExtension.fromJson(
        jsonSerialization['createdAt'],
      ),
    );
  }

  static final t = AgentStepTable();

  static const db = AgentStepRepository._();

  @override
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

  @override
  _is.Table<int?> get table => t;

  /// Returns a shallow copy of this [AgentStep]
  /// with some or all fields replaced by the given arguments.
  @_is.useResult
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

  static AgentStepInclude include() {
    return AgentStepInclude._();
  }

  static AgentStepIncludeList includeList({
    _is.WhereExpressionBuilder<AgentStepTable>? where,
    int? limit,
    int? offset,
    _is.OrderByBuilder<AgentStepTable>? orderBy,
    _is.OrderByListBuilder<AgentStepTable>? orderByList,
    AgentStepInclude? include,
  }) {
    return AgentStepIncludeList._(
      where: where,
      limit: limit,
      offset: offset,
      orderBy: orderBy?.call(AgentStep.t),
      orderByList: orderByList?.call(AgentStep.t),
      include: include,
    );
  }

  @override
  String toString() {
    return _is.SerializationManager.encode(this);
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
  @_is.useResult
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

class AgentStepUpdateTable extends _is.UpdateTable<AgentStepTable> {
  AgentStepUpdateTable(super.table);

  _is.ColumnValue<int, int> sessionId(int value) => _is.ColumnValue(
    table.sessionId,
    value,
  );

  _is.ColumnValue<int, int> index(int value) => _is.ColumnValue(
    table.index,
    value,
  );

  _is.ColumnValue<_ieq6bcjp.StepKind, _ieq6bcjp.StepKind> kind(
    _ieq6bcjp.StepKind value,
  ) => _is.ColumnValue(
    table.kind,
    value,
  );

  _is.ColumnValue<String, String> title(String value) => _is.ColumnValue(
    table.title,
    value,
  );

  _is.ColumnValue<String, String> detail(String value) => _is.ColumnValue(
    table.detail,
    value,
  );

  _is.ColumnValue<int, int> durationMs(int value) => _is.ColumnValue(
    table.durationMs,
    value,
  );

  _is.ColumnValue<DateTime, DateTime> createdAt(DateTime value) =>
      _is.ColumnValue(
        table.createdAt,
        value,
      );
}

class AgentStepTable extends _is.Table<int?> {
  AgentStepTable({super.tableRelation}) : super(tableName: 'agent_step') {
    updateTable = AgentStepUpdateTable(this);
    sessionId = _is.ColumnInt(
      'sessionId',
      this,
    );
    index = _is.ColumnInt(
      'index',
      this,
    );
    kind = _is.ColumnEnum(
      'kind',
      this,
      _is.EnumSerialization.byName,
    );
    title = _is.ColumnString(
      'title',
      this,
    );
    detail = _is.ColumnString(
      'detail',
      this,
    );
    durationMs = _is.ColumnInt(
      'durationMs',
      this,
    );
    createdAt = _is.ColumnDateTime(
      'createdAt',
      this,
    );
  }

  late final AgentStepUpdateTable updateTable;

  late final _is.ColumnInt sessionId;

  /// 1-based position in the session.
  late final _is.ColumnInt index;

  late final _is.ColumnEnum<_ieq6bcjp.StepKind> kind;

  late final _is.ColumnString title;

  /// The trace text, shown in a monospace font.
  late final _is.ColumnString detail;

  late final _is.ColumnInt durationMs;

  late final _is.ColumnDateTime createdAt;

  @override
  List<_is.Column> get columns => [
    id,
    sessionId,
    index,
    kind,
    title,
    detail,
    durationMs,
    createdAt,
  ];
}

class AgentStepInclude extends _is.IncludeObject {
  AgentStepInclude._();

  @override
  Map<String, _is.Include?> get includes => {};

  @override
  _is.Table<int?> get table => AgentStep.t;
}

class AgentStepIncludeList extends _is.IncludeList {
  AgentStepIncludeList._({
    _is.WhereExpressionBuilder<AgentStepTable>? where,
    super.limit,
    super.offset,
    super.orderBy,
    super.orderByList,
    super.include,
  }) {
    super.where = where?.call(AgentStep.t);
  }

  @override
  Map<String, _is.Include?> get includes => include?.includes ?? {};

  @override
  _is.Table<int?> get table => AgentStep.t;
}

class AgentStepRepository {
  const AgentStepRepository._();

  /// Returns a list of [AgentStep]s matching the given query parameters.
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
  Future<List<AgentStep>> find(
    _is.DatabaseSession session, {
    _is.WhereExpressionBuilder<AgentStepTable>? where,
    int? limit,
    int? offset,
    _is.OrderByBuilder<AgentStepTable>? orderBy,
    _is.OrderByListBuilder<AgentStepTable>? orderByList,
    _is.Transaction? transaction,
    _is.LockMode? lockMode,
    _is.LockBehavior? lockBehavior,
  }) async {
    return session.db.find<AgentStep>(
      where: where?.call(AgentStep.t),
      orderBy: orderBy?.call(AgentStep.t),
      orderByList: orderByList?.call(AgentStep.t),
      limit: limit,
      offset: offset,
      transaction: transaction,
      lockMode: lockMode,
      lockBehavior: lockBehavior,
    );
  }

  /// Emits [AgentStep]s matching the given query parameters every time the
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
  /// to that set. Pass [Table] instances such as `AgentStep.t`.
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
  _ida.Stream<List<AgentStep>> watch(
    _is.DatabaseSession session, {
    _is.WhereExpressionBuilder<AgentStepTable>? where,
    int? limit,
    int? offset,
    _is.OrderByBuilder<AgentStepTable>? orderBy,
    _is.OrderByListBuilder<AgentStepTable>? orderByList,
    Duration? throttle = const Duration(milliseconds: 30),
    Iterable<_is.Table>? alsoTriggerOnTables,
  }) {
    return session.db.watch<AgentStep>(
      where: where?.call(AgentStep.t),
      orderBy: orderBy?.call(AgentStep.t),
      orderByList: orderByList?.call(AgentStep.t),
      limit: limit,
      offset: offset,
      throttle: throttle,
      alsoTriggerOnTables: alsoTriggerOnTables,
    );
  }

  /// Returns the first matching [AgentStep] matching the given query parameters.
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
  Future<AgentStep?> findFirstRow(
    _is.DatabaseSession session, {
    _is.WhereExpressionBuilder<AgentStepTable>? where,
    int? offset,
    _is.OrderByBuilder<AgentStepTable>? orderBy,
    _is.OrderByListBuilder<AgentStepTable>? orderByList,
    _is.Transaction? transaction,
    _is.LockMode? lockMode,
    _is.LockBehavior? lockBehavior,
  }) async {
    return session.db.findFirstRow<AgentStep>(
      where: where?.call(AgentStep.t),
      orderBy: orderBy?.call(AgentStep.t),
      orderByList: orderByList?.call(AgentStep.t),
      offset: offset,
      transaction: transaction,
      lockMode: lockMode,
      lockBehavior: lockBehavior,
    );
  }

  /// Finds a single [AgentStep] by its [id] or null if no such row exists.
  Future<AgentStep?> findById(
    _is.DatabaseSession session,
    int id, {
    _is.Transaction? transaction,
    _is.LockMode? lockMode,
    _is.LockBehavior? lockBehavior,
  }) async {
    return session.db.findById<AgentStep>(
      id,
      transaction: transaction,
      lockMode: lockMode,
      lockBehavior: lockBehavior,
    );
  }

  /// Inserts all [AgentStep]s in the list and returns the inserted rows.
  ///
  /// The returned [AgentStep]s will have their `id` fields set.
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
  Future<List<AgentStep>> insert(
    _is.DatabaseSession session,
    List<AgentStep> rows, {
    _is.Transaction? transaction,
    bool ignoreConflicts = false,
    bool noReturn = false,
  }) async {
    return session.db.insert<AgentStep>(
      rows,
      transaction: transaction,
      ignoreConflicts: ignoreConflicts,
      noReturn: noReturn,
    );
  }

  /// Inserts a single [AgentStep] and returns the inserted row.
  ///
  /// The returned [AgentStep] will have its `id` field set.
  Future<AgentStep> insertRow(
    _is.DatabaseSession session,
    AgentStep row, {
    _is.Transaction? transaction,
  }) async {
    return session.db.insertRow<AgentStep>(
      row,
      transaction: transaction,
    );
  }

  /// Upserts all [AgentStep]s in the list and returns the resulting rows.
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
  /// The returned [AgentStep]s will have their `id` fields set.
  ///
  /// This is an atomic operation, meaning that if one of the rows fails,
  /// none of the rows will be affected.
  ///
  /// If [noReturn] is set to `true`, the resulting rows are not read back from
  /// the database and an empty list is returned. This avoids the overhead of
  /// transferring and deserializing the rows when the result is not needed.
  Future<List<AgentStep>> upsert(
    _is.DatabaseSession session,
    List<AgentStep> rows, {
    required _is.ColumnSelections<AgentStepTable> conflictColumns,
    _is.ColumnSelections<AgentStepTable>? updateColumns,
    _is.WhereExpressionBuilder<AgentStepTable>? updateWhere,
    _is.Transaction? transaction,
    bool noReturn = false,
  }) async {
    return session.db.upsert<AgentStep>(
      rows,
      conflictColumns: conflictColumns(AgentStep.t),
      updateColumns: updateColumns?.call(AgentStep.t),
      updateWhere: updateWhere?.call(AgentStep.t),
      transaction: transaction,
      noReturn: noReturn,
    );
  }

  /// Upserts a single [AgentStep] and returns the resulting row.
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
  /// The returned [AgentStep] will have its `id` field set.
  Future<AgentStep?> upsertRow(
    _is.DatabaseSession session,
    AgentStep row, {
    required _is.ColumnSelections<AgentStepTable> conflictColumns,
    _is.ColumnSelections<AgentStepTable>? updateColumns,
    _is.WhereExpressionBuilder<AgentStepTable>? updateWhere,
    _is.Transaction? transaction,
  }) async {
    return session.db.upsertRow<AgentStep>(
      row,
      conflictColumns: conflictColumns(AgentStep.t),
      updateColumns: updateColumns?.call(AgentStep.t),
      updateWhere: updateWhere?.call(AgentStep.t),
      transaction: transaction,
    );
  }

  /// Updates all [AgentStep]s in the list and returns the updated rows. If
  /// [columns] is provided, only those columns will be updated. Defaults to
  /// all columns.
  /// This is an atomic operation, meaning that if one of the rows fails to
  /// update, none of the rows will be updated.
  ///
  /// If [noReturn] is set to `true`, the updated rows are not read back from
  /// the database and an empty list is returned. This avoids the overhead of
  /// transferring and deserializing the rows when the result is not needed.
  Future<List<AgentStep>> update(
    _is.DatabaseSession session,
    List<AgentStep> rows, {
    _is.ColumnSelections<AgentStepTable>? columns,
    _is.Transaction? transaction,
    bool noReturn = false,
  }) async {
    return session.db.update<AgentStep>(
      rows,
      columns: columns?.call(AgentStep.t),
      transaction: transaction,
      noReturn: noReturn,
    );
  }

  /// Updates a single [AgentStep]. The row needs to have its id set.
  /// Optionally, a list of [columns] can be provided to only update those
  /// columns. Defaults to all columns.
  Future<AgentStep> updateRow(
    _is.DatabaseSession session,
    AgentStep row, {
    _is.ColumnSelections<AgentStepTable>? columns,
    _is.Transaction? transaction,
  }) async {
    return session.db.updateRow<AgentStep>(
      row,
      columns: columns?.call(AgentStep.t),
      transaction: transaction,
    );
  }

  /// Updates a single [AgentStep] by its [id] with the specified [columnValues].
  /// Returns the updated row or null if no row with the given id exists.
  Future<AgentStep?> updateById(
    _is.DatabaseSession session,
    int id, {
    required _is.ColumnValueListBuilder<AgentStepUpdateTable> columnValues,
    _is.Transaction? transaction,
  }) async {
    return session.db.updateById<AgentStep>(
      id,
      columnValues: columnValues(AgentStep.t.updateTable),
      transaction: transaction,
    );
  }

  /// Updates all [AgentStep]s matching the [where] expression with the specified [columnValues].
  /// Returns the list of updated rows.
  ///
  /// If [noReturn] is set to `true`, the updated rows are not read back from
  /// the database and an empty list is returned. This avoids the overhead of
  /// transferring and deserializing the rows when the result is not needed.
  Future<List<AgentStep>> updateWhere(
    _is.DatabaseSession session, {
    required _is.ColumnValueListBuilder<AgentStepUpdateTable> columnValues,
    required _is.WhereExpressionBuilder<AgentStepTable> where,
    int? limit,
    int? offset,
    _is.OrderByBuilder<AgentStepTable>? orderBy,
    _is.OrderByListBuilder<AgentStepTable>? orderByList,
    _is.Transaction? transaction,
    bool noReturn = false,
  }) async {
    return session.db.updateWhere<AgentStep>(
      columnValues: columnValues(AgentStep.t.updateTable),
      where: where(AgentStep.t),
      limit: limit,
      offset: offset,
      orderBy: orderBy?.call(AgentStep.t),
      orderByList: orderByList?.call(AgentStep.t),
      transaction: transaction,
      noReturn: noReturn,
    );
  }

  /// Deletes all [AgentStep]s in the list and returns the deleted rows.
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
  Future<List<AgentStep>> delete(
    _is.DatabaseSession session,
    List<AgentStep> rows, {
    _is.OrderByBuilder<AgentStepTable>? orderBy,
    _is.OrderByListBuilder<AgentStepTable>? orderByList,
    _is.Transaction? transaction,
    bool noReturn = false,
  }) async {
    return session.db.delete<AgentStep>(
      rows,
      orderBy: orderBy?.call(AgentStep.t),
      orderByList: orderByList?.call(AgentStep.t),
      transaction: transaction,
      noReturn: noReturn,
    );
  }

  /// Deletes a single [AgentStep].
  Future<AgentStep> deleteRow(
    _is.DatabaseSession session,
    AgentStep row, {
    _is.Transaction? transaction,
  }) async {
    return session.db.deleteRow<AgentStep>(
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
  Future<List<AgentStep>> deleteWhere(
    _is.DatabaseSession session, {
    required _is.WhereExpressionBuilder<AgentStepTable> where,
    _is.OrderByBuilder<AgentStepTable>? orderBy,
    _is.OrderByListBuilder<AgentStepTable>? orderByList,
    _is.Transaction? transaction,
    bool noReturn = false,
  }) async {
    return session.db.deleteWhere<AgentStep>(
      where: where(AgentStep.t),
      orderBy: orderBy?.call(AgentStep.t),
      orderByList: orderByList?.call(AgentStep.t),
      transaction: transaction,
      noReturn: noReturn,
    );
  }

  /// Counts the number of rows matching the [where] expression. If omitted,
  /// will return the count of all rows in the table.
  Future<int> count(
    _is.DatabaseSession session, {
    _is.WhereExpressionBuilder<AgentStepTable>? where,
    int? limit,
    _is.Transaction? transaction,
  }) async {
    return session.db.count<AgentStep>(
      where: where?.call(AgentStep.t),
      limit: limit,
      transaction: transaction,
    );
  }

  /// Acquires row-level locks on [AgentStep] rows matching the [where] expression.
  Future<void> lockRows(
    _is.DatabaseSession session, {
    required _is.WhereExpressionBuilder<AgentStepTable> where,
    required _is.LockMode lockMode,
    required _is.Transaction transaction,
    _is.LockBehavior lockBehavior = _is.LockBehavior.wait,
  }) async {
    return session.db.lockRows<AgentStep>(
      where: where(AgentStep.t),
      lockMode: lockMode,
      lockBehavior: lockBehavior,
      transaction: transaction,
    );
  }
}
