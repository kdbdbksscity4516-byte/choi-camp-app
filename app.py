// 1. 앱에서 보낸 정보를 기록하는 메인 함수
function doGet(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
    var data = sheet.getDataRange().getValues();
    var headers = data[0];
    
    var colIndex = headers.indexOf('참석여부') + 1;
    var timeColIndex = headers.indexOf('참석시간') + 1; // 누른 순서를 기록할 열
    
    if (colIndex === 0) return ContentService.createTextOutput("오류: '참석여부' 열을 찾을 수 없습니다.");

    var row = parseInt(e.parameter.row);
    var status = e.parameter.status;
    
    if (isNaN(row)) return ContentService.createTextOutput("에러: row 값이 없습니다.");

    // [상태 기록]
    sheet.getRange(row + 2, colIndex).setValue(status);
    
    // [참석시간 기록] - 이 시간이 지도의 선 긋는 순서가 됩니다.
    if (timeColIndex > 0) {
      if (status === "미체크") {
        sheet.getRange(row + 2, timeColIndex).clearContent(); // 재선택 시 시간 초기화
      } else {
        sheet.getRange(row + 2, timeColIndex).setValue(new Date()); // 현재 시간 기록
      }
    }
    
    // 기록 후 좌표가 비어있다면 자동으로 채우기
    fillCoords(); 

    return ContentService.createTextOutput("성공");
  } catch (f) {
    return ContentService.createTextOutput("에러: " + f.message);
  }
}

// 2. 주소를 위도/경도로 변환 (기존 기능 유지)
function fillCoords() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  
  var addrIdx = headers.indexOf("주소");
  var latIdx = headers.indexOf("위도");
  var lngIdx = headers.indexOf("경도");
  
  if (addrIdx == -1 || latIdx == -1 || lngIdx == -1) return;

  for (var i = 1; i < data.length; i++) {
    var address = data[i][addrIdx];
    if (address && (!data[i][latIdx] || !data[i][lngIdx])) {
      try {
        var response = Maps.newGeocoder().geocode(address);
        if (response.status == 'OK') {
          var res = response.results[0].geometry.location;
          sheet.getRange(i + 1, latIdx + 1).setValue(res.lat);
          sheet.getRange(i + 1, lngIdx + 1).setValue(res.lng);
        }
      } catch (e) {}
    }
  }
}

// 3. 시트 상단 메뉴 (기존 기능 유지)
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('🚀 캠프 도구')
      .addItem('📍 주소를 좌표로 변환', 'fillCoords')
      .addToUi();
}
