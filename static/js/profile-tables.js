$(document).ready(function() {
  var username = document.getElementById('twitter-username').innerHTML;
  $('#profile-table-following').DataTable( {
      "ajax": "/profile/" + username + "/following-list.json",
      "columns": [
          { "data": "username",
            "render": function ( data, type, row, meta ) {
              return '<a href="/profile/'+data+'">'+data+'</a>';
            } },
          { "data": "name" },
          { "data": "gender" },
          { "data": "followers" }
      ]
  } );
  $('#profile-table-followers').DataTable( {
      "ajax": "/profile/" + username + "/followers-list.json",
      "columns": [
          { "data": "username",
            "render": function ( data, type, row, meta ) {
              return '<a href="/profile/'+data+'">'+data+'</a>';
            } },
          { "data": "name" },
          { "data": "gender" },
          { "data": "followers" }
      ]
  } );
} );
