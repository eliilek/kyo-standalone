var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
const chatSocket = new ReconnectingWebSocket(
            ws_scheme
            + '://'
            + window.location.host
            + '/ws/chat/'
            + game_slug
            + '/'
        );

        chatSocket.onmessage = function(e) {
            const message = JSON.parse(e.data);
            $('#chat-log').val($("#chat-log").val() + message.message + '\n');
        };

        chatSocket.onclose = on_close_function

        $("#chat-message-input").on('keypress', function(e){
          if(e.which == 13){
            $("#chat-message-submit").click();
          }
        })

        $('#chat-message-submit').on('click', function(e){
          if($("#chat-message-input").val() == ""){
            return false;
          }
          const message = "P" + my_seat_number.toString() + ": " + $("#chat-message-input").val();
          const target = $("#message-target").val();
          console.log(target);
          chatSocket.send(JSON.stringify({'message': message, 'target': target}));
          $("#chat-message-input").val("");
          
        });