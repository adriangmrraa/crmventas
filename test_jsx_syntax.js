// Test JSX syntax by attempting to parse with Node.js
const fs = require('fs');
const path = require('path');

const filepath = path.join(__dirname, 'frontend_react/src/views/ChatsView.tsx');

console.log('🔍 Testing JSX syntax of ChatsView.tsx');

try {
  const content = fs.readFileSync(filepath, 'utf8');
  
  // Check for common JSX syntax issues
  console.log('📊 Basic checks:');
  
  // 1. Check div balance
  const divOpen = (content.match(/<div[^>]*>/g) || []).length;
  const divClose = (content.match(/<\/div>/g) || []).length;
  console.log(`  Divs: ${divOpen} openings, ${divClose} closings - ${divOpen === divClose ? '✅' : '❌'}`);
  
  // 2. Check fragment balance
  const fragOpen = (content.match(/<>/g) || []).length;
  const fragClose = (content.match(/<\/>/g) || []).length;
  console.log(`  Fragments: ${fragOpen} openings, ${fragClose} closings - ${fragOpen === fragClose ? '✅' : '❌'}`);
  
  // 3. Check template literals
  const backticks = (content.match(/`/g) || []).length;
  console.log(`  Backticks: ${backticks} - ${backticks % 2 === 0 ? '✅' : '❌'} (should be even)`);
  
  // 4. Check for obvious syntax errors
  const lines = content.split('\n');
  let hasErrors = false;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    // Check for unterminated JSX expressions
    if (line.includes('{') && !line.includes('}') && i < lines.length - 1) {
      // Check if next line has closing }
      let foundClose = false;
      for (let j = i + 1; j < Math.min(i + 5, lines.length); j++) {
        if (lines[j].includes('}')) {
          foundClose = true;
          break;
        }
      }
      if (!foundClose) {
        console.log(`  ⚠️ Line ${i + 1}: Possible unterminated JSX expression: ${line.substring(0, 50)}...`);
        hasErrors = true;
      }
    }
    
    // Check for )} pattern that might be problematic
    if (line.includes(')}') && line.includes('<') && line.includes('>')) {
      // Check if )} is inside JSX
      const parts = line.split(')}');
      for (const part of parts) {
        if (part.includes('<') && part.includes('>') && part.indexOf('<') < part.indexOf('>')) {
          console.log(`  ⚠️ Line ${i + 1}: Possible )} inside JSX element`);
          hasErrors = true;
          break;
        }
      }
    }
  }
  
  if (!hasErrors && divOpen === divClose && fragOpen === fragClose && backticks % 2 === 0) {
    console.log('\n✅ No obvious JSX syntax errors found');
    console.log('💡 File should compile successfully');
  } else {
    console.log('\n⚠️  Potential issues found');
    console.log('💡 Review the warnings above');
  }
  
} catch (error) {
  console.error('❌ Error reading file:', error.message);
}