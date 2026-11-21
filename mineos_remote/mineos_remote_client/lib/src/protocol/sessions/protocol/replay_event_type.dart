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

/// The kinds of event a replay stream sends.
enum ReplayEventType implements _isc.SerializableModel {
  /// The replay starts (again). The client clears its timeline.
  restart,

  /// One step is revealed.
  step,

  /// The agent is waiting on the model; label says for what.
  thinking,

  /// The agent is paused at its approval prompt. The stream ends.
  holding,

  /// The recording is over. The stream ends.
  finished;

  static ReplayEventType fromJson(String name) {
    switch (name) {
      case 'restart':
        return ReplayEventType.restart;
      case 'step':
        return ReplayEventType.step;
      case 'thinking':
        return ReplayEventType.thinking;
      case 'holding':
        return ReplayEventType.holding;
      case 'finished':
        return ReplayEventType.finished;
      default:
        throw ArgumentError(
          'Value "$name" cannot be converted to "ReplayEventType"',
        );
    }
  }

  @override
  String toJson() => name;

  @override
  String toString() => name;
}
