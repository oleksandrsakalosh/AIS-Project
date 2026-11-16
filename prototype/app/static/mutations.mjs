// One user action sends exactly one mutation. A lost response never causes a POST replay.
export async function submitOnce(send, reconcile) {
  let outcome;
  try {
    outcome = {ok: true, result: await send()};
  } catch (error) {
    outcome = {ok: false, error};
  }
  try {
    await reconcile();
    outcome.reconciled = true;
  } catch (error) {
    outcome.reconciled = false;
    outcome.reconcileError = error;
  }
  return outcome;
}
