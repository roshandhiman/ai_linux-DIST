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

/// What one step of an agent session is.
enum StepKind implements _isc.SerializableModel {
  /// The router's decision for the request.
  plan,

  /// A call to the local model (the slow part on a CPU).
  modelCall,

  /// A sandboxed run of the code the model wrote.
  toolCall,

  /// The agent's y/N prompt before it changes anything.
  approvalRequest,

  /// The turn's outcome and answer.
  result,

  /// A refused or failed block.
  error;

  static StepKind fromJson(String name) {
    switch (name) {
      case 'plan':
        return StepKind.plan;
      case 'modelCall':
        return StepKind.modelCall;
      case 'toolCall':
        return StepKind.toolCall;
      case 'approvalRequest':
        return StepKind.approvalRequest;
      case 'result':
        return StepKind.result;
      case 'error':
        return StepKind.error;
      default:
        throw ArgumentError('Value "$name" cannot be converted to "StepKind"');
    }
  }

  @override
  String toJson() => name;

  @override
  String toString() => name;
}
