const socket = io.connect();
const gameID  = window.location.pathname.split("/").pop();
const playerName = $("#player_name").text();


function sendNotification(notification) {
  UIkit.notification({
      message: notification,
      status: 'primary',
      pos: 'bottom-center',
      timeout: 3000
  });
}

function textToSpeech(text) {
  let msg = new SpeechSynthesisUtterance();
  msg.text = text;
  window.speechSynthesis.speak(msg);
}

socket.on('connect', function() {
  socket.emit("sendplayerinfo", {
    "playerID" : socket.id,
    "playerName" : playerName
  })
});

socket.on('disconnect', function() {
  console.log("Player Disconnected")
});

socket.on("notification", notification => {
  //Attach message in chatbox to keep persistent
  $("#chatmessages").append("<span>" + notification + "</span>");
  sendNotification(notification);
});

socket.on("sendbackmessage", message => {
  console.log(message)
  $("#chatmessages").append('<li>' + '<span class="uk-text-meta">' + message.player_name + "</span> <b>" + message.message + '</b></li>')

  function updateScroll(){
    var element = document.getElementById("chatbox");
    element.scrollTop = element.scrollHeight;
  }
  updateScroll();
})

$("#sendmessage").keypress(function( event ) {
  if (event.which == 13) {
    let message = $(this).val();
    if (!message) {
        alert("Please enter a valid message");
        return;
    }
    socket.emit("sendmessage", { "player_name" : playerName, "message" : message })
    $(this).val("");
  }
});

socket.on('renderScoreBoard', players => {
  let output = "";
  let i;
  output += "<table class='uk-table uk-table-striped uk-table-small'><tbody>"
  for (i = 0; i < players.length; i++) {
    output += `<tr class = "playerrow">
                <td width="40px"><img class="uk-border-circle" width="40" height="40" src="../static/avatars/${players[i].avatar}"></td>
                <td>${players[i].player_name}<br><span class="uk-badge">${players[i].score} points</span></td>
                <td class="uk-align-right uk-text-meta">${players[i].player_state}</td>
              </tr>`
  }
  output += "</tbody></table>";
  output = "<div id ='leaderboardinner'>" + output + "</div>";
  $("#leaderboard").html(output);
});


$("#startgame").on("click", function () {
  if ($(".playerrow").length >= 1) {
    socket.emit("startgame");
    $(this).hide();
  } else {
    alert("Need at least 2 players to start");
  }
})

socket.on('emitstartgame', data => {
    $("#definitioninput").focus();
    $("#submitdefinition").removeClass("uk-disabled");
    $("#submitdefinition").removeClass("uk-hidden");
    $("#submitdefinition").addClass("uk-animation-scale-down");
    $("#submitdefinition").prop("disabled", false);
    let currentRoundNumber = data.current_round_num;
    let totalRoundNum = data.total_rounds;
    $("#round").text("Round " + currentRoundNumber + " / " + totalRoundNum);
    $("#word").text(data['word_set'][0]['word']);
    $("#word").addClass("uk-animation-slide-right");
    $("#startgame").addClass("uk-hidden");
    document.title = "Game Starting";

    textToSpeech("Round " + currentRoundNumber + ". " + $("#word").text());

});

socket.on("waitingforplayers", data => {

});

$("#submitdefinition").on("click", function () {
  let definition = $("#definitioninput").val();
  definition = definition.replace(/<{1}[^<>]{1,}>{1}/g," "); //Remove Tags
  definition = definition.charAt(0).toLowerCase() + definition.slice(1); //lowercase first character
  if (definition[definition.length-1] === ".") {
    definition = definition.slice(0,-1);
  }
  if (!definition) {
    alert("Please submit a valid definition");
    return;
  }
  $(this).addClass("uk-disabled");
  $(this).prop("disabled", true);
  socket.emit("submitdefinition", { "playerName" : playerName, "definition" : definition})

  document.getElementById("submitsound").play();

})

socket.on("showdefinitions", players => {
  let output = "";
  let i;
  for (i = 0; i < players.length; i++) {
    output += `<div class="uk-margin uk-width-1-1"><div class="uk-card uk-card-default uk-card-body uk-card-small uk-card-hover uk-animation-slide-top-medium">
                <h3 class="uk-card-title answercardheader" data-player="${players[i].player_name}"><span class="uk-badge">${i + 1}</span></h3>
                <p>${players[i].definition}</p>
                <button class="uk-button uk-button-danger uk-animation-scale-down vote" data-player="${players[i].player_name}">
                  VOTE
                </button>
                <hr class="uk-divider-small">
                <span class = "uk-text-meta votenum"></span>
                <ul class="uk-list" id="${players[i].player_name.replace(/ /g,'')}_votes_for">
                </ul>
              </div></div>`
  }
  $("#definitions").html(output)
  document.title = "It's voting time!";
  textToSpeech(document.title);
})

$(document).on("click", ".vote", function () {
  let voteFor = $(this).attr("data-player");
  $(".vote").hide();
  socket.emit("vote", { "voteFrom" : playerName, "voteFor" : voteFor })

  document.getElementById("votesound").play();
})

socket.on("revealanswers", data => {
  $("#submitdefinition").removeClass("uk-animation-scale-down"); //Todo this shouldn't be here
  $("#word").removeClass("uk-animation-slide-right") //Todo this shouldn't be here
  //Reveal players above their answer cards
  $('.answercardheader').each(function(i, obj) {
    $(obj).addClass("uk-animation-scale-down");
    let answerName = $(obj).attr("data-player")
    $(obj).text(answerName);
    if (answerName == "Dictionary Definition") {
      //Change background color of entire card
      $(obj).parent().removeClass("uk-card-default").addClass("uk-card-primary");
    }
  });
  //Render votes for list under each player's card, binds to ID and ID cannot have spaces in it
  for (let i = 0; i < data.length; i++) {
    $div = $("#" + data[i]['votes_for'].replace(/ /g,'') + "_votes_for")
    $div.append("<li>" + "<img src = " + "../static/avatars/" +
            data[i]['avatar'] + " width='25px'> " +
            data[i]['player_name'] + "</li>");
    $div.prev().text("Votes: " + $div.children().length)
  }

  //Reveal next round button
  $("#nextround").removeClass("uk-hidden")
  $("#nextround").addClass("uk-animation-scale-down");

  document.title = "Everyone voted! See results."
  textToSpeech("Everyone voted!")
});

$("#nextround").on("click", function () {
  socket.emit("startnextround");
})

socket.on("nextroundstarting", data => {
  $("#nextround").addClass("uk-hidden");
  $("#round").removeClass("uk-hidden");
  $("#definitioninput").focus();
  //Clear last answer
  $("#definitioninput").val("");
  $("#submitdefinition").removeClass("uk-disabled");
  $("#submitdefinition").addClass("uk-animation-scale-down");
  $("#submitdefinition").prop("disabled", false);
  let currentRoundNumber = data.current_round_num;
  let totalRoundNum = data.total_rounds;
  $("#round").text("Round " + currentRoundNumber + " / " + totalRoundNum);
  $("#word").text(data.word_set[currentRoundNumber - 1].word);
  $("#word").addClass("uk-animation-slide-right")
  $("#definitions").html("");

  document.title = "Next Round Starting";
  textToSpeech("Round " + currentRoundNumber + ". " + $("#word").text());
});

socket.on("showmatchsummary", data => {
  $("#gamesummary").removeClass("uk-hidden");
  $("#nextround").addClass("uk-hidden");
  output = ""
  output += `<div class="uk-card uk-card-primary uk-card-body uk-margin">
                  <h3 class="uk-card-title">Winners</h3>
                  <p>${data.winning_players}</p>
              </div>`
  output += `<div class="uk-card uk-card-muted uk-card-body uk-margin">
                  <h3 class="uk-card-title">Most Correct Votes</h3>
                  <p>${data.most_correct_players}</p>
              </div>`
  output += `<div class="uk-card uk-card-secondary uk-card-body uk-margin">
                  <h3 class="uk-card-title">Losers</h3>
                  <p>${data.losing_players}</p>
              </div>`

  for (let i = 0; i < data.total_rounds; i++) {
    output += `<div class="uk-card uk-card-default uk-card-body uk-margin">
                  <div class="uk-card-badge uk-label">Round ${i + 1}</div>
                  <h3 class="uk-card-title">${data.word_set[i]['word']}</h3>
                  <p>${data.word_set[i]['definition']}</p>`

    output += '<hr class="uk-divider-icon">'
    output += '<dl class="uk-description-list uk-description-list-divider">'
    for (let j = 0; j < data.players.length; j++) {
      output += "<dt>" + data.players[j].player_name + "</dt>"
      output += "<dd>" + data.players[j]['definitions'][String(i + 1)] + "</dd>"
    }
    output += "</dl>"
  output += "</div>"
  }
  $("#summarybody").html(output);
  document.title = "Dictionarygame.io"
});
