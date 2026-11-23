const catalogPath = '/api/admin/catalog';
const accountPath = '/api/admin/accounts';
const recoveryKey = 'pohyb.catalog.create-recovery';
const uncertainErrors = ['network', 'storage_unavailable', 'internal_error'];
const catalogMessages = {
  catalog_entry_not_found: 'Položka sa nenašla. Skontrolujte aktuálny zoznam.',
  catalog_entry_changed: 'Položka sa medzitým zmenila.',
  catalog_entry_inactive: 'K neaktívnemu trénerovi nemožno priradiť účet.',
  catalog_name_taken: 'Tento názov už používa iná položka v katalógu vrátane neaktívnych položiek.',
  create_request_conflict: 'Tento pokus o vytvorenie už bol použitý s iným názvom.',
  future_training_reference: 'Na položku odkazuje budúci tréning. Deaktivácia je možná po jeho začiatku alebo po úprave rozvrhu, keď bude dostupná.',
  future_training_assignment: 'Tréner má budúci tréning. Prepojenie možno zmeniť po jeho začiatku alebo po úprave rozvrhu, keď bude dostupná.',
  trainer_account_ineligible: 'Vyberte aktívny účet s rolou Tréner.',
  trainer_account_already_linked: 'Účet je už priradený k inému trénerovi. Najprv zrušte jeho existujúce prepojenie.',
  network: 'Výsledok požiadavky sa nepodarilo overiť.'
};

export function clearCatalogRecovery() {
  try { sessionStorage.removeItem(recoveryKey); } catch {}
}

function restoreCreates(adminId) {
  try {
    const saved = JSON.parse(sessionStorage.getItem(recoveryKey));
    if (saved?.adminId === adminId) return new Map(Object.entries(saved.intents));
  } catch {}
  clearCatalogRecovery();
  return new Map();
}

export async function setupCatalog({adminId, api, element, notice, messages}) {
  const panel = document.querySelector('#catalog');
  const find = selector => panel.querySelector(selector);
  const kindSelect = find('#catalog-kind');
  const refresh = find('#catalog-refresh');
  const list = find('#catalog-list');
  const create = find('#catalog-create');
  const createName = create.elements.name;
  const createButton = create.querySelector('button');
  const unresolvedCreates = restoreCreates(adminId);
  let items = [], accounts = null, available = false, pending = false;

  const kind = () => kindSelect.value;
  const path = () => `${catalogPath}/${kind()}`;
  const feedback = error => catalogMessages[error.code] || messages[error.code] || messages.internal_error;

  function persistCreates() {
    try {
      if (unresolvedCreates.size) {
        const intents = Object.fromEntries(unresolvedCreates);
        sessionStorage.setItem(recoveryKey, JSON.stringify({adminId, intents}));
      } else {
        sessionStorage.removeItem(recoveryKey);
      }
      return true;
    } catch {
      return false;
    }
  }

  function forgetCreate() {
    unresolvedCreates.delete(kind());
    persistCreates();
  }

  function updateControls() {
    kindSelect.disabled = refresh.disabled = pending;
    create.querySelector('fieldset').disabled = pending || !available;
    for (const fieldset of list.querySelectorAll('fieldset')) {
      fieldset.disabled = pending || !available || (fieldset.dataset.picker === 'true' && !accounts);
    }
  }

  function showCreateIntent() {
    const intent = unresolvedCreates.get(kind());
    if (intent) createName.value = intent.name;
    createName.readOnly = Boolean(intent);
    createButton.textContent = intent ? 'Overiť vytvorenie' : 'Pridať položku';
  }

  function addOption(select, id, label) {
    const option = element('option', '', label);
    option.value = id ?? '';
    select.append(option);
  }

  function editForm(title, labelText, field, onSave, help = '') {
    const details = element('details', 'catalog-editor');
    details.append(element('summary', '', title));
    const form = element('form');
    const fields = element('fieldset');
    const label = element('label', '', labelText);
    label.htmlFor = field.id;
    fields.append(label, field);
    if (help) fields.append(element('p', 'muted', help));
    const actions = element('div', 'catalog-form-actions');
    const submit = element('button', 'button button-outline', 'Uložiť');
    const cancel = element('button', 'button button-outline', 'Zavrieť');
    cancel.type = 'button';
    cancel.addEventListener('click', () => {
      form.reset();
      details.open = false;
      details.querySelector('summary').focus();
    });
    actions.append(submit, cancel);
    fields.append(actions);
    form.append(fields);
    form.addEventListener('submit', event => {
      event.preventDefault();
      onSave(field.value);
    });
    details.append(form);
    return details;
  }

  function trainerFields(row, entry) {
    const account = accounts?.find(user => user.id === entry.account_id);
    const linked = account ? `@${account.username}` : `účet č. ${entry.account_id}`;
    let description = 'Bez prepojenia';
    if (entry.account_id !== null) {
      const effective = entry.status === 'active' && account?.role === 'trainer' && account.status === 'active';
      const state = !accounts ? '' : effective ? ' · aktívne prepojenie' : ' · neúčinné prepojenie';
      description = linked + state;
    }
    row.append(element('p', 'muted', description));
    if (entry.status === 'inactive' && entry.account_id === null) return;

    const select = element('select');
    select.id = `trainer-account-${entry.id}`;
    addOption(select, null, 'Bez prepojenia');
    if (entry.account_id !== null) addOption(select, entry.account_id, linked);
    if (entry.status === 'active' && accounts) {
      const linkedIds = new Set(items.map(item => item.account_id));
      for (const user of accounts) {
        if (user.role === 'trainer' && user.status === 'active' && !linkedIds.has(user.id)) {
          addOption(select, user.id, `${user.display_name} (@${user.username})`);
        }
      }
    }
    select.value = entry.account_id ?? '';
    for (const option of select.options) option.defaultSelected = option.selected;
    const help = entry.account_id === null
      ? 'Vybraný účet prepojíte s týmto trénerom aj s jeho už naplánovanými tréningmi.' : '';
    const editor = editForm('Prepojenie účtu', 'Účet trénera', select,
      value => save('account', {account_id: value ? Number(value) : null}, entry), help);
    editor.querySelector('fieldset').dataset.picker = 'true';
    row.append(editor);
  }

  function card(entry) {
    const row = element('article', 'admin-account');
    row.dataset.entryId = entry.id;
    const title = kind() === 'trainers' ? `${entry.name} · č. ${entry.id}` : entry.name;
    row.append(element('h3', '', title), element('p', 'admin-status', entry.status === 'active' ? 'Aktívna položka' : 'Neaktívna položka'));

    const name = element('input');
    name.id = `catalog-name-${entry.id}`;
    name.defaultValue = entry.name;
    name.required = true;
    row.append(editForm('Premenovať', 'Názov', name, value => save('name', {name: value}, entry)));
    if (entry.status === 'active') {
      const deactivate = element('button', 'button button-outline', 'Deaktivovať');
      deactivate.type = 'button';
      deactivate.addEventListener('click', () => save('status', {status: 'inactive'}, entry));
      const fields = element('fieldset', 'catalog-deactivate');
      fields.append(deactivate);
      row.append(fields);
    }
    if (kind() === 'trainers') trainerFields(row, entry);
    return row;
  }

  async function load() {
    available = false;
    list.setAttribute('aria-busy', 'true');
    updateControls();
    const [catalogResult, accountsResult] = await Promise.allSettled([
      api(path()), kind() === 'trainers' ? api(accountPath) : Promise.resolve(null)
    ]);
    if (!panel.isConnected) return false;
    accounts = accountsResult.status === 'fulfilled' ? accountsResult.value?.items ?? null : null;
    find('#catalog-picker-error').hidden = kind() !== 'trainers' || accounts !== null;
    list.setAttribute('aria-busy', 'false');
    if (catalogResult.status === 'rejected') {
      if (!items.length) list.replaceChildren(element('p', 'empty', 'Zoznam sa nepodarilo načítať.'));
      return false;
    }
    items = catalogResult.value.items;
    list.replaceChildren(...items.map(card));
    if (!items.length) list.append(element('p', 'empty', 'Zoznam je prázdny.'));
    available = true;
    return true;
  }

  async function reload() {
    if (pending) return;
    pending = true;
    const loaded = await load();
    pending = false;
    if (!panel.isConnected) return;
    updateControls();
    const recovery = unresolvedCreates.has(kind()) ? ' Tlačidlom Overiť vytvorenie môžete overiť pôvodnú požiadavku.' : '';
    notice(loaded ? `Zoznam je aktuálny.${recovery}` : 'Zoznam sa nepodarilo načítať. Obnovte údaje.', !loaded);
  }

  async function save(field, data, entry) {
    if (pending || !available) return;
    const retryingCreate = !entry && unresolvedCreates.has(kind());
    if (!entry && !retryingCreate) {
      // Save the key before sending so navigation during the POST is recoverable too.
      unresolvedCreates.set(kind(), data);
      if (!persistCreates()) {
        unresolvedCreates.delete(kind());
        notice('Údaje na bezpečné zopakovanie sa nepodarilo uložiť. Obnovte stránku a skúste znova.', true);
        return;
      }
    }
    pending = true;
    updateControls();
    if (entry) data.expected_version = entry.version;
    try {
      const saved = await api(entry ? `${path()}/${entry.id}/${field}` : path(), {
        method: entry ? 'PUT' : 'POST', body: JSON.stringify(data)
      });
      if (!entry) {
        forgetCreate();
        create.reset();
        showCreateIntent();
      }
      const loaded = await load();
      if (panel.isConnected) {
        const summary = entry ? 'Zmena bola uložená.' : `Položka č. ${saved.id} bola vytvorená.`;
        notice(loaded ? summary : `${summary} Pred ďalšou úpravou obnovte zoznam.`, !loaded);
      }
    } catch (error) {
      if (!panel.isConnected) return;
      const uncertain = uncertainErrors.includes(error.code);
      if (!entry) {
        if (!uncertain && !(retryingCreate && error.code === 'csrf_invalid')) forgetCreate();
        showCreateIntent();
      }
      if (uncertain || ['catalog_entry_changed', 'catalog_entry_not_found'].includes(error.code)) {
        const loaded = await load();
        if (!panel.isConnected) return;
        const current = entry && items.find(item => item.id === entry.id);
        const state = current ? `Aktuálny záznam: ${current.name}, verzia ${current.version}.` : '';
        const next = entry ? `${state} Skontrolujte zoznam pred ďalšou zmenou.`
          : 'Tlačidlom Overiť vytvorenie môžete overiť pôvodnú požiadavku.';
        notice(`${feedback(error)} ${loaded ? next : 'Pred ďalšou úpravou obnovte zoznam.'}`, true);
      } else {
        notice(feedback(error), true);
      }
    } finally {
      pending = false;
      if (panel.isConnected) updateControls();
    }
  }

  create.addEventListener('submit', event => {
    event.preventDefault();
    const data = unresolvedCreates.get(kind()) ?? {name: createName.value, request_id: crypto.randomUUID()};
    return save(null, data);
  });
  refresh.addEventListener('click', reload);
  kindSelect.addEventListener('change', () => {
    items = [];
    list.replaceChildren(element('p', 'empty', 'Načítavam katalóg…'));
    find('#catalog-title').textContent = kindSelect.selectedOptions[0].textContent;
    create.reset();
    showCreateIntent();
    reload();
  });
  showCreateIntent();
  await reload();
}
