const $ = id => document.getElementById(id);
const actor = 'demo-person';
let selected = null;
let key = null;
async function api(path, value) {
  const response = await fetch(path, value === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(value)
  });
  const data = await response.json();
  if (!response.ok) throw Error(data.error || 'Request failed');
  return data;
}
function message(text) { $('message').textContent = text; }
function bind(id, work) {
  $(id).addEventListener('click', async () => {
    $(id).disabled = true;
    try { await work(); message('Saved in this synthetic local demo.'); }
    catch (error) { message(error.message); }
    finally { if (id === 'suggest') $(id).disabled = false; }
  });
}
function showState(intent) {
  $('state').textContent = intent.status + ' · ' + intent.listing + ' / ' + intent.slot +
    ' · source ' + intent.source + (intent.receipt ? ' · synthetic receipt ' + intent.receipt : '');
  $('approve').disabled = intent.status !== 'PROPOSED';
  $('unknown').disabled = intent.status !== 'PENDING_PROVIDER';
  $('confirm').disabled = !['PENDING_PROVIDER','RECONCILING'].includes(intent.status);
  refreshEvents().catch(error => message(error.message));
}
async function refreshEvents() {
  if (!key) return;
  const events = await api('/api/events?key=' + encodeURIComponent(key) + '&actor=' + actor);
  const list = $('events'); list.replaceChildren();
  for (const event of events) {
    const item = document.createElement('li'); item.textContent = event.status + ': ' + event.reason; list.append(item);
  }
}
async function propose(option) {
  selected = option;
  key = crypto.randomUUID();
  showState(await api('/api/propose', {key, actor, source: 'assistant',
    listing_id: option.listing_id, slot_id: option.slot_id}));
}
bind('suggest', async () => {
  const result = await api('/api/suggest', {request: $('request').value});
  $('suggestion').textContent = result.option.listing_id + ' / ' + result.option.slot_id +
    ' — ' + result.reason + ' (proposal only)';
  await propose(result.option);
});
bind('approve', async () => { showState(await api('/api/approve', {key, actor, consent: true})); });
bind('unknown', async () => { showState(await api('/api/provider', {key, outcome: 'unknown', receipt: null})); });
bind('confirm', async () => { showState(await api('/api/provider', {key, outcome: 'confirmed', receipt: 'sandbox-' + key.slice(0,8)})); });
api('/api/options').then(result => {
  for (const option of result.options) {
    const row = document.createElement('div'); row.className = 'slot';
    const name = document.createElement('strong'); name.textContent = option.listing_id + ' · ' + option.slot_id;
    const detail = document.createElement('small'); detail.textContent = option.provider + ' · logical start ' + option.start_at;
    const button = document.createElement('button'); button.textContent = 'Propose this option';
    button.addEventListener('click', () => propose(option).catch(error => message(error.message)));
    row.append(name, detail, document.createElement('br'), button); $('options').append(row);
  }
}).catch(error => message(error.message));
