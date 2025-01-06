// !function($) {
//     "use strict";

//     var CalendarPage = function() {};

//     CalendarPage.prototype.init = function() {

//         //checking if plugin is available
//         if ($.isFunction($.fn.fullCalendar)) {
//             /* initialize the calendar */
//             $('#calendar').fullCalendar({
//                 header: {
//                     left: 'prev,next today',
//                     center: 'title',
//                     right: 'month,basicWeek,basicDay'
//                 },
//                 events: function(start, end, timezone, callback) {
//                     $.ajax({
//                         url: '{% url "appointment_list" %}',  // URL to fetch appointments
//                         dataType: 'json',
//                         success: function(data) {
//                             var events = [];
//                             $(data).each(function() {
//                                 events.push({
//                                     title: this.title,
//                                     start: this.start,
//                                     end: this.end,
//                                     allDay: this.allDay
//                                 });
//                             });
//                             callback(events);
//                         }
//                     });
//                 }
//             });

//         } else {
//             alert("Calendar plugin is not installed");
//         }
//     },
//     //init
//     $.CalendarPage = new CalendarPage, $.CalendarPage.Constructor = CalendarPage
// }(window.jQuery),

// //initializing 
// function($) {
//     "use strict";
//     $.CalendarPage.init()
// }(window.jQuery);