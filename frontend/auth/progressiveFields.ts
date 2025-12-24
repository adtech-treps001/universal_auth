
/**
 * Global progressive profiling logic.
 * Applies to ALL workflows.
 */
export function getVisibleFields(order, context) {
  return order.filter(field =>
    context.required_fields.includes(field) ||
    context.optional_fields.includes(field)
  );
}
