/**
 * Marketing Integration Test Script
 * Sprint 2 - Day 5: Sidebar Integration & Routing Testing
 * 
 * This script tests the frontend integration without running the full app.
 * It verifies file structure, imports, and basic functionality.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('🔍 MARKETING INTEGRATION TESTING');
console.log('=' .repeat(60));

const baseDir = path.join(__dirname, 'src');
let passed = 0;
let total = 0;

function test(description, condition) {
  total++;
  const status = condition ? '✅' : '❌';
  console.log(`${status} ${description}`);
  if (condition) passed++;
  return condition;
}

function checkFileExists(filePath, description) {
  const exists = fs.existsSync(filePath);
  return test(`${description}: ${filePath}`, exists);
}

function checkFileContent(filePath, requiredStrings, description) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const results = requiredStrings.map(([string, desc]) => {
      const found = content.includes(string);
      test(`  ${desc} in ${path.basename(filePath)}`, found);
      return found;
    });
    return results.every(r => r);
  } catch (error) {
    return test(`${description}: Error reading file`, false);
  }
}

function checkTypeScriptImports(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    // Check for common import issues
    const checks = [
      ['import.*from', 'Has imports'],
      ['export.*function|export.*const|export.*default', 'Has exports'],
      ['React', 'Uses React'],
    ];
    
    console.log(`  📦 Checking ${path.basename(filePath)} imports...`);
    return checks.map(([pattern, desc]) => {
      const regex = new RegExp(pattern);
      const found = regex.test(content);
      test(`    ${desc}`, found);
      return found;
    }).every(r => r);
  } catch (error) {
    return test(`Error checking ${filePath}`, false);
  }
}

// ==================== TEST SUITE ====================

console.log('\n📁 FILE STRUCTURE TESTS');
console.log('-'.repeat(40));

// Check directory structure
const dirsToCheck = [
  ['views/marketing', 'Marketing views directory'],
  ['components/marketing', 'Marketing components directory'],
  ['api', 'API directory'],
  ['types', 'Types directory'],
];

dirsToCheck.forEach(([dir, desc]) => {
  const dirPath = path.join(baseDir, dir);
  checkFileExists(dirPath, desc);
});

console.log('\n📄 COMPONENT FILES TESTS');
console.log('-'.repeat(40));

// Check component files
const componentFiles = [
  ['views/marketing/MarketingHubView.tsx', 'MarketingHubView'],
  ['views/marketing/MetaTemplatesView.tsx', 'MetaTemplatesView'],
  ['components/marketing/MarketingPerformanceCard.tsx', 'MarketingPerformanceCard'],
  ['components/marketing/MetaConnectionWizard.tsx', 'MetaConnectionWizard'],
  ['components/marketing/MetaTokenBanner.tsx', 'MetaTokenBanner'],
  ['api/marketing.ts', 'Marketing API client'],
  ['types/marketing.ts', 'Marketing TypeScript types'],
];

componentFiles.forEach(([file, desc]) => {
  const filePath = path.join(baseDir, file);
  if (checkFileExists(filePath, desc)) {
    checkTypeScriptImports(filePath);
  }
});

console.log('\n🔗 ROUTING INTEGRATION TESTS');
console.log('-'.repeat(40));

// Check App.tsx integration
const appFile = path.join(baseDir, 'App.tsx');
if (checkFileExists(appFile, 'App.tsx')) {
  checkFileContent(appFile, [
    ['MarketingHubView', 'Imports MarketingHubView'],
    ['MetaTemplatesView', 'Imports MetaTemplatesView'],
    ['/crm/marketing', 'Has /crm/marketing route'],
    ['/crm/hsm', 'Has /crm/hsm route'],
    ['ProtectedRoute.*allowedRoles.*\\[.*ceo.*admin.*marketing.*\\]', 'Has role protection for marketing'],
    ['ProtectedRoute.*allowedRoles.*\\[.*ceo.*admin.*\\]', 'Has role protection for HSM'],
  ], 'App.tsx routing integration');
}

console.log('\n🧭 SIDEBAR INTEGRATION TESTS');
console.log('-'.repeat(40));

// Check Sidebar.tsx integration
const sidebarFile = path.join(baseDir, 'components/Sidebar.tsx');
if (checkFileExists(sidebarFile, 'Sidebar.tsx')) {
  checkFileContent(sidebarFile, [
    ['Megaphone', 'Imports Megaphone icon'],
    ['Layout', 'Imports Layout icon'],
    ['marketing.*labelKey.*nav.marketing', 'Has marketing menu item'],
    ['hsm_automation.*labelKey.*nav.hsm_automation', 'Has HSM automation menu item'],
    ['/crm/marketing.*isActive', 'Has /crm/marketing in isActive function'],
    ['/crm/hsm.*isActive', 'Has /crm/hsm in isActive function'],
  ], 'Sidebar integration');
}

console.log('\n🌐 I18N INTEGRATION TESTS');
console.log('-'.repeat(40));

// Check translations
const localesDir = path.join(baseDir, 'locales');
const localeFiles = ['es.json', 'en.json'];

localeFiles.forEach(file => {
  const filePath = path.join(localesDir, file);
  if (checkFileExists(filePath, `${file} translations`)) {
    checkFileContent(filePath, [
      ['"marketing"', `Has "marketing" key in ${file}`],
      ['"hsm_automation"', `Has "hsm_automation" key in ${file}`],
    ], `${file} content`);
  }
});

console.log('\n📦 PACKAGE.JSON DEPENDENCIES CHECK');
console.log('-'.repeat(40));

// Check package.json for required dependencies
const packageFile = path.join(__dirname, 'package.json');
if (checkFileExists(packageFile, 'package.json')) {
  try {
    const packageJson = JSON.parse(fs.readFileSync(packageFile, 'utf8'));
    
    // Check for React Router
    const hasReactRouter = packageJson.dependencies?.['react-router-dom'] || 
                          packageJson.devDependencies?.['react-router-dom'];
    test('Has react-router-dom dependency', hasReactRouter);
    
    // Check for lucide-react (icons)
    const hasLucideReact = packageJson.dependencies?.['lucide-react'] || 
                          packageJson.devDependencies?.['lucide-react'];
    test('Has lucide-react dependency (for icons)', hasLucideReact);
    
    // Check for TypeScript
    const hasTypeScript = packageJson.dependencies?.['typescript'] || 
                         packageJson.devDependencies?.['typescript'];
    test('Has TypeScript', hasTypeScript);
    
  } catch (error) {
    test('Error reading package.json', false);
  }
}

console.log('\n🔗 API CLIENT TESTS');
console.log('-'.repeat(40));

// Check API client
const apiFile = path.join(baseDir, 'api/marketing.ts');
if (checkFileExists(apiFile, 'Marketing API client')) {
  checkFileContent(apiFile, [
    ['getStats', 'Has getStats function'],
    ['getMetaPortfolios', 'Has getMetaPortfolios function'],
    ['getHSMTemplates', 'Has getHSMTemplates function'],
    ['getCampaigns', 'Has getCampaigns function'],
    ['getMetaAuthUrl', 'Has getMetaAuthUrl function'],
    ['formatCurrency', 'Has formatCurrency helper'],
    ['formatPercentage', 'Has formatPercentage helper'],
    ['MarketingStats', 'Exports MarketingStats interface'],
    ['CampaignStat', 'Exports CampaignStat interface'],
  ], 'API client functionality');
}

console.log('\n📝 TYPE DEFINITIONS TESTS');
console.log('-'.repeat(40));

// Check TypeScript types
const typesFile = path.join(baseDir, 'types/marketing.ts');
if (checkFileExists(typesFile, 'Marketing TypeScript types')) {
  checkFileContent(typesFile, [
    ['interface MarketingStats', 'Has MarketingStats interface'],
    ['interface CampaignStat', 'Has CampaignStat interface'],
    ['interface MetaTokenStatus', 'Has MetaTokenStatus interface'],
    ['interface HSMTemplate', 'Has HSMTemplate interface'],
    ['enum TimeRange', 'Has TimeRange enum'],
    ['enum CampaignStatus', 'Has CampaignStatus enum'],
  ], 'TypeScript types completeness');
}

console.log('\n' + '='.repeat(60));
console.log('📊 TEST RESULTS SUMMARY');
console.log('='.repeat(60));

const percentage = Math.round((passed / total) * 100);
console.log(`\n🎯 ${passed}/${total} tests passed (${percentage}%)`);

if (passed === total) {
  console.log('\n🎉 EXCELLENT! All integration tests passed.');
  console.log('✅ Sprint 2 Day 5 (Integration Testing) is complete.');
  console.log('\n📋 Ready for Day 6 (Component Testing & Optimization).');
} else if (percentage >= 80) {
  console.log('\n⚠️ GOOD: Most tests passed. Review failed tests above.');
  console.log('Proceed to Day 6 with noted issues.');
} else {
  console.log('\n❌ NEEDS WORK: Significant integration issues found.');
  console.log('Fix failed tests before proceeding.');
}

console.log('\n🔧 NEXT STEPS:');
console.log('1. Run actual React dev server: npm run dev');
console.log('2. Navigate to /crm/marketing to test routing');
console.log('3. Test sidebar navigation items');
console.log('4. Verify API client works with backend');
console.log('5. Create component unit tests (Day 6)');

process.exit(passed === total ? 0 : 1);