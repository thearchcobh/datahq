// The Arch: automatically updated widget. Keep this script on your phone.
const endpoint = 'https://tqrgwcixxifzdzsphdxj.supabase.co/functions/v1/arch-labour-widget';
const key = 'thearch.labour.widget.token.v1';
const fm = FileManager.local();
const cache = fm.joinPath(fm.libraryDirectory(), 'arch-widget-code-v1.json');
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
let widget;
async function run(bundle, saved) {
  if (bundle.protocol !== 1 || typeof bundle.code !== 'string' || bundle.code.length > 100000) {
    throw Error('Invalid widget update');
  }
  const result = await new AsyncFunction('ctx', bundle.code)({endpoint, key, saved});
  if (!result || typeof result.addText !== 'function') throw Error('Invalid widget');
  return result;
}
try {
  if (!Keychain.contains(key)) throw Error('Run your original widget once to connect.');
  try {
    const request = new Request(endpoint + '?asset=widget');
    request.headers = {Authorization: 'Bearer ' + Keychain.get(key)};
    request.timeoutInterval = 10;
    const bundle = await request.loadJSON();
    if (request.response.statusCode === 401) {
      if (fm.fileExists(cache)) fm.remove(cache);
      throw Error('Widget access key rejected.');
    }
    if (request.response.statusCode !== 200) throw Error('Update unavailable');
    widget = await run(bundle, false);
    try { fm.writeString(cache, JSON.stringify(bundle)); } catch {}
  } catch (error) {
    if (!fm.fileExists(cache)) throw error;
    widget = await run(JSON.parse(fm.readString(cache)), true);
  }
} catch (error) {
  widget = new ListWidget();
  widget.addText('The Arch');
  widget.addText(String(error.message || error));
}
widget.refreshAfterDate = new Date(Date.now() + 15 * 60000);
widget.url = 'scriptable:///run?scriptName=' + encodeURIComponent(Script.name());
Script.setWidget(widget);
if (!config.runsInWidget) await widget.presentMedium();
Script.complete();
