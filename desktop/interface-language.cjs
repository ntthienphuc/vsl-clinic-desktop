'use strict';

const fs = require('node:fs');
const path = require('node:path');

/** Store only the interface preference; no conversation or recognition state. */
module.exports = function interfaceLanguage(profileDirectory) {
  const file = path.join(profileDirectory, 'interface-language.json');
  let language = 'vi';
  try {
    const saved = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (saved.language === 'vi' || saved.language === 'en') language = saved.language;
  } catch { /* Missing or invalid preferences use Vietnamese. */ }
  return {
    get: () => language,
    set: value => {
      if (value !== 'vi' && value !== 'en') throw new Error('Unsupported interface language');
      fs.mkdirSync(profileDirectory, { recursive: true });
      const temporary = file + '.tmp';
      fs.writeFileSync(temporary, JSON.stringify({ language: value }) + '\n', 'utf8');
      fs.renameSync(temporary, file);
      language = value;
      return language;
    },
  };
};
