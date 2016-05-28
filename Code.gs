/*
BernieEventBot. Google Spreadsheet side of the script

Copyright (C) 2016  Brennan Lujan

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

/*
 data is expected to be a 2d array
      0   1      2     3       4    5     6
 x: [ID, date, RSVPs, title, city, URL, Address]
 y: data set
*/
function UpdateCDSheet (
  data,
  district
) {
  var ss = SpreadsheetApp.openById('')
  if (district == 6) {
    var sheet = ss.getSheets()[0]; // Get first Sheet
  } else if (district == 7) {
    var sheet = ss.getSheets()[1]; // Get second Sheet
  } else if (district == 4) {
    var sheet = ss.getSheets()[2]; // Get third Sheet
  }
  Logger.log(sheet.getName());

  var current_lastrow = sheet.getLastRow() - 1; // Skip header
  var current_lastcolumn = sheet.getLastColumn();
  var current = sheet.getRange(2, 1, current_lastrow, current_lastcolumn).getValues()
  
  // 1. Grayout old events
  var current_time = new Date().getTime();
  var colors = new Array(current_lastrow);
  for (var y = 0; y < current_lastrow; y++) {
    colors[y] = new Array(current_lastcolumn);
    var event_datetime = new Date(current[y][1]);
    if (event_datetime < current_time) {
      for (var x = 0; x < current_lastcolumn; x++) {
        colors[y][x] = "#A0A0A0";
      }
    }
  }
  sheet.getRange(2, 1, current_lastrow, current_lastcolumn).setFontColors(colors);

  // 2. Update RSVP numbers (based on ID)
  for (var y = 0; y < current_lastrow; y++) {
    for (var yy = 0; yy < data.length; yy++) {
      if (current[y][0] == data[yy][0]) { // If IDs match
        current[y][2] = data[yy][2];
        current[y][4] = data[yy][4];
      }
    }
  }
  sheet.getRange(2, 1, current_lastrow, current_lastcolumn).setValues(current)

  // 3. Add New events
  for (var y = 0; y < data.length; y++) {
    var Found = false;
    for (var yy = 0; yy < current_lastrow; yy++) {
      if (current[yy][0] == data[y][0]) {
          Found = true;
      }
    }
    if (Found == false) {
      sheet.appendRow(data[y])
      var range = sheet.getRange(sheet.getLastRow(), 2)
      range.setNumberFormat("DDDD MM/dd h:mm am/pm")
    }
  }
         
  // 4. Sort the list
  sheet.sort(2)
}

