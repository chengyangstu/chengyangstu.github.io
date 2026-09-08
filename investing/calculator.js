'use strict';

function dcfValue({cashflow, growth, discount, terminal, extra, shares}) {
  if (![cashflow, growth, discount, terminal, extra, shares].every(Number.isFinite) ||
      cashflow < 0 || growth < -99 || growth > 100 || discount <= 0 ||
      discount > 100 || terminal < -99 || terminal > 20 || shares <= 0)
    throw new Error('请输入有效数字；现金流不得为负、股本须大于零，增长率和折现率须在标注范围内。');
  if (discount <= terminal) throw new Error('股权折现率必须大于永续增长率。');
  const r = discount / 100, g = growth / 100, gt = terminal / 100;
  let cash = cashflow, present = 0;
  for (let year = 1; year <= 5; year++) {
    cash *= 1 + g;
    present += cash / (1 + r) ** year;
  }
  const terminalPresent = cash * (1 + gt) / (r - gt) / (1 + r) ** 5;
  const operating = present + terminalPresent;
  const perShare = (operating + extra) / shares;
  if (![operating, perShare].every(Number.isFinite)) throw new Error('输入超出可计算范围，请缩小数值。');
  return {perShare, terminalPercent: operating ? 100 * terminalPresent / operating : 0};
}

if (typeof module !== 'undefined') module.exports = dcfValue;
if (typeof document !== 'undefined') {
  const form = document.getElementById('dcf-form');
  const output = document.getElementById('dcf-result');
  function update() {
    try {
      const values = Object.fromEntries([...form.elements].filter(el => el.name)
        .map(el => [el.name, el.value.trim() === '' ? NaN : Number(el.value)]));
      const {perShare, terminalPercent} = dcfValue(values);
      output.textContent = '每股模型价值 ' + perShare.toFixed(2) + ' 元；终值占经营部分现值 ' +
        terminalPercent.toFixed(1) + '%。这是输入假设的结果。';
      output.classList.remove('invalid');
    } catch (error) {
      output.textContent = error.message;
      output.classList.add('invalid');
    }
  }
  form.addEventListener('submit', event => { event.preventDefault(); update(); });
  form.addEventListener('input', update);
  update();
}
