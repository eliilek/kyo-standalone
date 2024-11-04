function on_close_function(e){
   console.log("Socket closed unexpectedly.");
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
var pre_pause_button_disabled;
var game_paused = false;
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
        if ("instructions" in data){
        		$("#instructions-span").html(data['instructions']);
        	}
        if ("background" in data){
        	$(".flex-body").css("background", data['background']);
        }
        if("game_start" in data){
        	if ((!sequential_turns) || "your_move" in data){
        		alert("Game has started, it's your move!");
        		$("#choice-row").removeClass("not-turn");
	        	$(".choice-td").click(choice_click);
        	} else {
        		alert("Game has started")
        	}
        } else if ("game_pause" in data){
        	alert("The experimenter has paused the game");
        	pre_pause_button_disabled = $("#submit-choice-button").prop("disabled");
        	$("#submit-choice-button").prop("disabled", true);
        	game_paused = true;
        } else if ("game_resume" in data){
        	alert("The experimenter has resumed the game");
        	game_paused = false;
        	$("#submit-choice-button").prop("disabled", pre_pause_button_disabled);
        } else if ("game_end" in data){
        	alert("The game has ended. Thank you for playing!");
        	window.location.reload(true);
        } else if ("points" in data){
        	for (key in data["points"]){
        		if ($("td.points-body[data-instance-name=" + key + "]").length != 0){
        			$("td.points-body[data-instance-name=" + key + "]").html(data["points"][key]);
        		}
        	}
        	if ("current_choice_pk" in data){
        		$(".selected-choice").removeClass("selected-choice");
        		$(".choice-td[data-choice-pk=" + data['current_choice_pk'] + "]").addClass("selected-choice");
        		$("#submit-choice-button").prop("disabled", true);
        		$(".choice-td").off('click');
        		$("#choice-row").addClass('not-turn');
        	} else if ((!sequential_turns) || "your_move" in data){
        		$("#choice-row").removeClass("not-turn");
						$(".choice-td").click(choice_click);
        	}
        	for (func in results_functions){
        		results_functions[func](data);
        	}
        	if ("current_choices" in data){
            for (key in data['current_choices']){
              if ($("#current-cycle-table").length != 0){
                $("#current-cycle-img-player-" + key).prop('src', get_image_url(data[key]));
              }
              if (my_seat_number == parseInt(key)){
        				$(".selected-choice").removeClass("selected-choice");
        				$(".choice-td[data-choice-pk=" + data[key] + "]").addClass("selected-choice");
        				$("#submit-choice-button").prop("disabled", true);
        				$(".choice-td").off('click');
        				$("#choice-row").addClass('not-turn');
        			}
            }
            if ((!sequential_turns) || "your_move" in data){
            		$("#choice-row").removeClass('not-turn');
								$(".choice-td").click(choice_click);
            }
          }
        } else if ("choice_pk" in data){
        	if ($("#current-cycle-table").length != 0){
        		$("#current-cycle-img-player-" + data['seat']).prop('src', get_image_url(data['choice_pk']));
        	}
        	if (sequential_turns && "your_move" in data){
        		$("#choice-row").removeClass('not-turn');
        		$(".choice-td").click(choice_click);
        		$(".selected-choice").removeClass("selected-choice");
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
        	if ("game_end" in data['results']){
        		alert_str += "The game has ended. Please get instructions from your experimenter"
        		//TODO Do any cleanup required
        		$("#game-announcements-span").html(alert_str);
        		$(".selected-choice").removeClass("selected-choice");
        		return false;
        	}
        	if (alert_str != "" && alert_str != undefined){
        		$("#game-announcements-span").html(alert_str);
        } else if (alert_str != undefined){
        	$("#game-announcements-span").html("");
        	alert("Next round");
        }
        $(".selected-choice").removeClass("selected-choice");

					if ($("#current-cycle-table").length != 0){
        		$(".current-cycle-img").each(function(){
        			$(this).prop('src', "");
        		});
        	}

        if ((!sequential_turns) || "your_move" in data){
        	$("#choice-row").removeClass("not-turn");
	        $(".choice-td").click(choice_click);
        	}
        	if ("paused" in data){
        		pre_pause_button_disabled = $("#submit-choice-button").prop("disabled");
        		$("#submit-choice-button").prop("disabled", true);
        		game_paused = true;
        	}
        };
    	}

      resultsSocket.onclose = on_close_function

function choice_click(){
	if (game_paused){
		return false;
	}
				$(".selected-choice").removeClass("selected-choice");
				$(this).addClass("selected-choice");
				$("#submit-choice-button").prop("disabled", false);
}

$(document).ready(function(){
	if(game_started){
		resultsSocket.onopen = function(){
			resultsSocket.send(JSON.stringify({'refresh_results': true}))
		}
	}
	$("#submit-choice-button").prop("disabled", true);
	$("#submit-choice-button").click(function(){
		if($(".selected-choice").length == 0 || confirm("Are you sure you want to make this choice?") == false){
			return false;
		}
		resultsSocket.send(JSON.stringify({'choice': $(".selected-choice").data('choice-pk')}));
		$("#submit-choice-button").prop("disabled", true);
		$(".choice-td").off('click');
		$("#choice-row").addClass('not-turn');
	});
	$(".flex-body").css("background-color", background_color);
});

window.onerror = function(message, source, lineno, colno, error) {
   alert(message);
   resultsSocket.send(JSON.stringify({'error':error, 'source':source, 'lineno':lineno, 'colno':colno, message:'message'}))
}