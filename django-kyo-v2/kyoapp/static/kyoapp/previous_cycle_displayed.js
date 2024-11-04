//#results['moves'] = [(choice, seat_number)]

function previous_cycle_displayed_results(data){
	if (data['results']){
		for (move in data['results']['moves']){
			$("#previous-cycle-img-player-" + data['results']['moves'][move][1]).prop('src', get_image_url(data['results']['moves'][move][0]))
		}
	}
}

results_functions.push(previous_cycle_displayed_results);