function doGet(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  
  // '참석여부'라는 글자가 있는 열 번호를 자동으로 찾습니다.
  var colIndex = headers.indexOf('참석여부') + 1;
  
  if (colIndex === 0) {
    return ContentService.createTextOutput("오류: '참석여부' 열을 찾을 수 없습니다.");
  }

  var row = parseInt(e.parameter.row) + 1; // 헤더 제외 인덱스 보정
  var status = e.parameter.status;
  
  // 해당 칸에 글자를 씁니다.
  sheet.getRange(row + 1, colIndex).setValue(status); 
  
  return ContentService.createTextOutput("성공");
}
