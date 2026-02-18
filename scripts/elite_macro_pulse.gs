/**
 * Elite v20 Macro Pulse - Auto Refresh Script
 * ============================================
 * Auto-refreshes GOOGLEFINANCE() formulas every 60 seconds
 * Handles errors and provides fallback values
 * 
 * Setup:
 * 1. Tools → Script editor
 * 2. Paste this code
 * 3. Run setup() once
 * 4. Authorize
 */

// Configuration
const REFRESH_INTERVAL_SECONDS = 60;
const SHEET_NAME = "Macro Data";

/**
 * Initial setup - Run once to create trigger
 */
function setup() {
  // Delete existing triggers
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => ScriptApp.deleteTrigger(trigger));
  
  // Create time-based trigger for auto-refresh
  ScriptApp.newTrigger('refreshMacroData')
    .timeBased()
    .everyMinutes(1)
    .create();
  
  Logger.log('✅ Auto-refresh trigger created (every 1 minute)');
  
  // Initial refresh
  refreshMacroData();
}

/**
 * Main refresh function - runs every minute
 */
function refreshMacroData() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  
  if (!sheet) {
    Logger.log('❌ Sheet not found: ' + SHEET_NAME);
    return;
  }
  
  try {
    // Force recalculation by touching the cells
    const range = sheet.getRange('B1:B5');
    const formulas = range.getFormulas();
    
    // Re-set formulas to force refresh
    range.setFormulas(formulas);
    
    // Update timestamp
    sheet.getRange('D1').setValue(new Date());
    
    Logger.log('✅ Macro data refreshed at: ' + new Date());
    
    // Export to JSON
    exportToJSON();
    
  } catch (error) {
    Logger.log('⚠️ Refresh error: ' + error);
    handleError(sheet, error);
  }
}

/**
 * Export data to JSON format (for Python)
 */
function exportToJSON() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  
  try {
    // Get values
    const btcPrice = sheet.getRange('B1').getValue();
    const vix = sheet.getRange('B2').getValue();
    const sp500 = sheet.getRange('B3').getValue();
    const etfFlow = sheet.getRange('B4').getValue();
    const sentiment = sheet.getRange('B5').getValue();
    
    // Create JSON object
    const data = {
      "btc_price": Number(btcPrice) || 0,
      "vix": Number(vix) || 0,
      "sp500_change": Number(sp500) || 0,
      "btc_etf_flow_24h": Number(etfFlow) || 0,
      "sentiment": sentiment || "Neutral",
      "timestamp": new Date().toISOString(),
      "status": "live"
    };
    
    // Write JSON to cell A10
    const jsonString = JSON.stringify(data, null, 2);
    sheet.getRange('A10').setValue(jsonString);
    
    Logger.log('✅ JSON exported to A10');
    
  } catch (error) {
    Logger.log('⚠️ JSON export error: ' + error);
  }
}

/**
 * Handle errors with fallback values
 */
function handleError(sheet, error) {
  // Get previous values as fallback
  const lastGoodValues = sheet.getRange('F1:F5').getValues();
  
  // If formulas fail, use cached values
  if (!sheet.getRange('B1').getValue()) {
    sheet.getRange('B1').setValue(lastGoodValues[0][0] || 0);
  }
  if (!sheet.getRange('B2').getValue()) {
    sheet.getRange('B2').setValue(lastGoodValues[1][0] || 20);
  }
  if (!sheet.getRange('B3').getValue()) {
    sheet.getRange('B3').setValue(lastGoodValues[2][0] || 0);
  }
  
  // Show error message
  sheet.getRange('D2').setValue('⚠️ Error: ' + error.toString().substring(0, 50));
}

/**
 * Cache current values (run every hour)
 */
function cacheValues() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  
  // Copy current values to cache column
  const values = sheet.getRange('B1:B5').getValues();
  sheet.getRange('F1:F5').setValues(values);
  
  Logger.log('✅ Values cached');
}

/**
 * Manual refresh button function
 */
function manualRefresh() {
  refreshMacroData();
  SpreadsheetApp.getActiveSpreadsheet().toast('✅ Macro data refreshed!', 'Success', 3);
}
