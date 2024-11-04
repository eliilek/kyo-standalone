function on_close_function(e){
   console.log("Socket closed unexpectedly.");
   //TODO Handle in some way?
   //alert("Websocket closed unexpectedly. Please refresh the page.")
   }

function get_image_url(pk){
	try{
		return $("td[data-choice-pk=" + pk + "] img").prop("src");
	} catch {
		console.log("Bad choice PK");
		return ""
	}
}
var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
const resultsSocket = new ReconnectingWebSocket(
            ws_scheme
            + '://'
            + window.location.host
            + '/ws/results/'
            + game_slug
            + '/'
            );
      resultsSocket.onmessage = function(e){
        const data = JSON.parse(e.data)
        console.log(data);
        if ("points" in data){
        	for (key in data["points"]){
        		if ($("td.points-body[data-instance-name=" + key + "]").length != 0){
        			$("td.points-body[data-instance-name=" + key + "]").html(data["points"][key]);
        		}
        	}
        	for (func in results_functions){
        		results_functions[func](data);
        	}
          if ("current_choices" in data){
            for (key in data['current_choices']){
              if ($("#current-cycle-table").length != 0){
                $("#current-cycle-img-player-" + key).prop('src', get_image_url(data['current_choices'][key]));
              }
            }
          }
        } else if ("choice_pk" in data){
        	if ($("#current-cycle-table").length != 0){
        		$("#current-cycle-img-player-" + data['seat']).prop('src', get_image_url(data['choice_pk']));
        	}
        } else {
        	var alert_str = "";
        	for (key in data['results']){
        		if (key != "moves"){
        			//Key is point name, see if that's one we have
        			if ($("td.points-body[data-instance-name=" + key + "]").length != 0){
        				for (tuple in data['results'][key]){
        					$("td.points-body[data-instance-name=" + key + "]").html((parseInt($("td.points-body[data-instance-name=" + key + "]").html()) + parseInt(data['results'][key][tuple][0])).toString())
        					if (data['results'][key][tuple].length == 2 || data['results'][key][tuple][2] != false){
                    if (data['results'][key][tuple][2] === true){
                      if (parseInt(data['results'][key][tuple][0]) > 0){
                        alert_str += $("td.points-body[data-instance-name=" + key + "]").data("instance-display") + " increased " + data['results'][key][tuple][0].toString() + " points by player " + data['results'][key][tuple][1].toString().replace("GROUP", "admin") + "<br>"
                      } else {
                        alert_str += $("td.points-body[data-instance-name=" + key + "]").data("instance-display") + " decreased " + data['results'][key][tuple][0].toString() + " points by player " + data['results'][key][tuple][1].toString().replace("GROUP", "admin") + "<br>"
                      }
                    } else {
                      alert_str += data['results'][key][tuple][2].toString() + "<br>"
                    }
                  }
        				}
        			}
        		}
        	}
        	for (func in results_functions){
        		results_functions[func](data);
        	}
          if (alert_str != "" && alert_str != undefined){
          alert(alert_str);
        } else if (alert_str != undefined){
          alert("Next round");
        }
          $("#current-condition-cycle-span").html(data['current_cycle'].toString());
          $("#total-cycle-span").html(data['total_cycle'].toString());
        if ($("#current-cycle-table").length != 0){
          $(".current-cycle-img").each(function(){
            $(this).prop('src', "");
          });
        }
        };

        
    	}

      resultsSocket.onclose = on_close_function

$(document).ready(function(){
	if(game_started){
		resultsSocket.onopen = function(){
			resultsSocket.send(JSON.stringify({'refresh_results': true}))
		}
    $("#pause-button").click(function(){
      if ($("#pause-button").html() == "Pause Game"){
        $("#pause-button").html("Resume Game");
        resultsSocket.send(JSON.stringify({'pause_game': true}));
      } else {
        $("#pause-button").html("Pause Game");
        resultsSocket.send(JSON.stringify({'resume_game': true}));
      }
    });
    $("#end-button").click(function(){
      if (confirm("Are you sure you want to end this game?")){
        resultsSocket.send(JSON.stringify({'end_game': true}));
      }
    })
	}
	$("#start-button").click(function(){
		resultsSocket.send(JSON.stringify({'start_game': true}));
		$("#start-button").remove();
      $("col-2").append("<button id='pause-button'>Pause Game</button>");
      $("col-2").append("<button id='end-button'>End Game</button>");
    $("#current-condition-cycle-span").html("1");
    $("#total-cycle-span").html("1");
    $("#pause-button").click(function(){
      if ($("#pause-button").html() == "Pause Game"){
        $("#pause-button").html("Resume Game");
        resultsSocket.send(JSON.stringify({'pause_game': true}));
      } else {
        $("#pause-button").html("Pause Game");
        resultsSocket.send(JSON.stringify({'resume_game': true}));
      }
    });
    $("#end-button").click(function(){
      if (confirm("Are you sure you want to end this game?")){
        resultsSocket.send(JSON.stringify({'end_game': true}));
      }
    })
	})
})