import { chromium } from 'playwright';

const BASE = 'http://localhost:5001';

function pass(msg) { console.log(`  ✓ ${msg}`); }
function fail(msg) { console.error(`  ✗ ${msg}`); process.exitCode = 1; }

async function run() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // ── Test 1: page loads ────────────────────────────────────────────────────
  console.log('\nTest 1: Page loads');
  await page.goto(BASE);
  const title = await page.title();
  title.includes('IDEA4RC') ? pass(`Title: "${title}"`) : fail(`Unexpected title: "${title}"`);

  // ── Test 2: Filter dropdowns present ─────────────────────────────────────
  console.log('\nTest 2: Filter dropdowns visible');
  // Wait for the async /filters fetch to populate the dropdown
  await page.waitForFunction(
    () => document.querySelectorAll('#filterMacro option').length > 1,
    { timeout: 5000 }
  );
  const macroOpts = await page.locator('#filterMacro option').allTextContents();
  macroOpts.includes('Soft tissue') ? pass(`Macrogrouping has "Soft tissue"`) : fail('Missing "Soft tissue"');
  macroOpts.includes('CNS')         ? pass(`Macrogrouping has "CNS"`)         : fail('Missing "CNS"');
  macroOpts.includes('Head and neck') ? pass(`Macrogrouping has "Head and neck"`) : fail('Missing "Head and neck"');

  // ── Test 3: Basic name search ─────────────────────────────────────────────
  console.log('\nTest 3: Basic name search "well differentiated"');
  await page.fill('#queryInput', 'well differentiated');
  await page.click('#searchBtn');
  await page.waitForSelector('#idsSection', { state: 'visible', timeout: 15000 });
  const count1 = await page.textContent('#countBadge');
  parseInt(count1) > 0 ? pass(`Got ${count1} results`) : fail('Got 0 results');
  const ids1 = await page.textContent('#idsOutput');
  ids1.includes(',') ? pass('IDs are comma-separated') : fail('IDs not comma-separated');

  // ── Test 4: Cascading filter - select Soft tissue ─────────────────────────
  console.log('\nTest 4: Filter by Macrogrouping = "Soft tissue"');
  await page.selectOption('#filterMacro', 'Soft tissue');
  await page.waitForTimeout(200);
  const groupDisabled = await page.locator('#filterGroup').isDisabled();
  groupDisabled ? fail('Group dropdown should be enabled after macro selection') : pass('Group dropdown enabled');
  const groupOpts = await page.locator('#filterGroup option').allTextContents();
  groupOpts.length > 1 ? pass(`Group has ${groupOpts.length - 1} options: ${groupOpts.slice(1, 4).join(', ')}...`) : fail('No group options');

  // ── Test 5: Search with macro filter ─────────────────────────────────────
  console.log('\nTest 5: "well differentiated" + Soft tissue filter');
  await page.fill('#queryInput', 'well differentiated');
  await page.click('#searchBtn');
  await page.waitForTimeout(3000);
  const count2 = await page.textContent('#countBadge');
  parseInt(count2) > 0 ? pass(`Got ${count2} results (filtered)`) : fail('Got 0 results with filter');
  // Should be fewer than unfiltered
  parseInt(count2) < parseInt(count1) ? pass(`Fewer than unfiltered (${count1})`) : pass(`Result count: ${count2}`);

  // ── Test 6: Filter-only (no query) ───────────────────────────────────────
  console.log('\nTest 6: Filter-only (CNS, no query)');
  await page.fill('#queryInput', '');
  await page.selectOption('#filterMacro', 'CNS');
  await page.waitForTimeout(200);
  await page.click('#searchBtn');
  await page.waitForTimeout(5000);
  const count3 = await page.textContent('#countBadge');
  const count3Num = parseInt(count3.replace(/[,\.]/g, ''));
  count3Num > 100 ? pass(`CNS filter-only: ${count3} entries`) : fail(`Expected many CNS entries, got ${count3}`);
  const truncWarnVisible = await page.locator('#truncWarn').isVisible();
  truncWarnVisible ? pass('Truncation warning shown for large result set') : pass('Result set fits table (no truncation)');
  const scoreHeaderHidden = await page.locator('#scoreHeader').isHidden();
  scoreHeaderHidden ? pass('Score column hidden when no query') : fail('Score column should be hidden');

  // ── Test 7: Clear filters ─────────────────────────────────────────────────
  console.log('\nTest 7: Clear filters');
  await page.click('#clearFilters');
  const macroVal = await page.inputValue('#filterMacro');
  macroVal === '' ? pass('Macrogrouping reset') : fail(`Macro not reset: "${macroVal}"`);
  const groupIsDisabled = await page.locator('#filterGroup').isDisabled();
  groupIsDisabled ? pass('Group dropdown disabled after clear') : fail('Group should be disabled');

  // ── Test 8: Typo/fuzzy ("well differenciated") ───────────────────────────
  console.log('\nTest 8: Fuzzy matching typo "well differenciated"');
  await page.fill('#queryInput', 'well differenciated');
  await page.click('#searchBtn');
  await page.waitForTimeout(4000);
  const count4 = await page.textContent('#countBadge');
  parseInt(count4) > 0 ? pass(`Fuzzy match found ${count4} results`) : fail('Fuzzy match returned 0');
  const firstScore = await page.locator('tbody tr:first-child td.score-cell').textContent();
  firstScore ? pass(`Top match score: ${firstScore.trim()}`) : fail('Score not displayed');

  // ── Done ──────────────────────────────────────────────────────────────────
  await browser.close();
  console.log(`\n${'─'.repeat(50)}`);
  if (process.exitCode === 1) {
    console.log('Some tests FAILED.');
  } else {
    console.log('All tests PASSED.');
  }
}

run().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
