app.views.client = Backbone.View.extend({
		template: _.template($("#tpl-page-2").html()),
		events: {
				'click .event_word_btn': 'timeline_btn',
				'click #reset_impact': 'reset_impact',
				'click .tl_options_btn': 'mark_event',
				'click .cluster_tweets': 'cluster_tweets',
				'click .tweet_state': 'tweet_state',
        		'click .scroll_tweets': 'scroll_tweets',
				'click .cluster_state': 'cluster_state',
				'click .btn_filter': 'filter_tweets'
		},
	  initialize: function() {
	      this.render();
	      var handler = _.bind(this.render, this);
	      var self = this;
	      $(document).on("click","body .tweet_state",function(e){
			self.tweet_state(e);
		});
	  },
	  render: function(){
	    var html = this.template({});
	  	this.$el.html(html);
	  	this.delegateEvents();
	  	$('#timeline_div').html('<div id="timeline-embed" style="width: 100%; height: 800px;box-shadow: 0 4px 2px -2px rgba(0,0,0,0.2)"></div>');
		this.load_timeline();
		this.load_impact();
	  	return this;
	  },
		load_timeline: function(){
			var self = this;
			console.log("Timeline");
			data = app.eventsCollection.get_timeline_events();
			if($('#timeline-embed').length){
				timeline = new TL.Timeline('timeline-embed',data,{
					timenav_height: 260,
					marker_height_min: 40
				});
				var s_ev = app.eventsCollection.get({ cid: timeline.config.events[0].unique_id }).toJSON();
				var t0 = performance.now();
				$.post(app.appURL+'event_tweets', {obj: JSON.stringify(s_ev), index: app.session.s_index}, function(response){
					self.display_tweets(response, t0, timeline.config.events[0].unique_id);
				}, 'json');

				timeline.on('change', function(data) {
						var ev = app.eventsCollection.get({ cid: data.unique_id }).toJSON();
						 self.load_impact(ev.main_term);
						$('#tweets_results').fadeOut('slow');
			      $('.loading_text').fadeIn('slow');
			      var t0 = performance.now();
					$.post(app.appURL+'event_tweets', {obj: JSON.stringify(ev), index: app.session.s_index}, function(response){
						self.display_tweets(response, t0, data.unique_id);
					}, 'json');
				});
			}
		},
		reset_impact: function(e){
			e.preventDefault();
			this.load_impact();
			return false;
		},
		load_impact: function(event){
			if($('#chartDiv').length){
					$('#chartDiv').fadeOut('slow');

					var event_impact = JSON.parse(app.session.impact_data);
					if(event){
						$.each(event_impact, function(i, e){
							if(e.key!=event){
								var opacity = (Math.floor(Math.random() * 10) + 1)*0.1;
								e.color = 'rgba(0,0,0,'+ opacity +')';
							}
						});
					}
					var chart;
					nv.addGraph(function() {
							chart = nv.models.stackedAreaChart()
									.useInteractiveGuideline(true)
									.x(function(d) { return d[0] })
									.y(function(d) { return d[1] })
									.controlLabels({stacked: "Stacked"});

							chart.yAxis.scale().domain([0, 20]);
							chart.xAxis.tickFormat(function(d) { return d3.time.format('%x')(new Date(d)) });
							chart.yAxis.tickFormat(d3.format(',.4f'));
							chart.height(300);

							chart.legend.vers('furious');

							chart.showControls(false);
							$('#chartDiv').html('<svg id="chart1" style="height: 300px;"></svg>')
							var output = d3.select('#chart1')
									.datum(event_impact)
									.call(chart);
							nv.utils.windowResize(chart.update);
							return chart;
					});
					$('#chartDiv').fadeIn('slow');
			}

		},
		timeline_btn: function(e){
			e.preventDefault();
			var self = this;
			var word = $(e.currentTarget).data("value");
			$('#tweets_results').fadeOut('slow');
			$('.loading_text').fadeIn('slow');
			var t0 = performance.now();
			$.post(app.appURL+'tweets', {word:word, index: app.session.s_index}, function(response){
						self.display_tweets(response, t0);
			}, 'json');

			return false;
		},
		mark_event: function(e){
			e.preventDefault();
			var self = this;
			var s_ev = JSON.stringify(app.eventsCollection.get({ cid: $(e.currentTarget).data("cid") }).toJSON());
			var data = [];
			data.push({name: "index", value: app.session.s_index});
			data.push({name: "session", value: app.session.s_name});
			data.push({name: "event", value: s_ev});
			data.push({name: "status", value: $(e.currentTarget).data("status")});

			 var jc = $.confirm({
				theme: 'pix-default-modal',
				title: 'Changing tweets state',
				boxWidth: '600px',
				useBootstrap: false,
				backgroundDismiss: false,
				content: 'Please Don\'t close the page.<div class=" jconfirm-box jconfirm-hilight-shake jconfirm-type-default  jconfirm-type-animated loading" role="dialog"></div>',
				defaultButtons: false,
				buttons: {
					cancel: {
						text: 'OK',
						btnClass: 'btn-cancel'
					}
				}
			});

			$.post(app.appURL+'mark_event', data, function(response){
				jc.close();
						console.log(response);
			}, 'json');
			return false;
		},
		cluster_tweets: function(e){
			e.preventDefault();
			var self = this;
			var cid = $(e.currentTarget).data("cid");
			var ev = app.eventsCollection.get({ cid: $(e.currentTarget).data("eid") }).toJSON();

			$.confirm({
					theme: 'pix-cluster-modal',
					title: 'Cluster'+cid+' Tweets',
					columnClass: 'col-md-12',
					useBootstrap: true,
					backgroundDismiss: false,
					// content: html,
					content: 'Loading... <div class=" jconfirm-box jconfirm-hilight-shake jconfirm-type-default  jconfirm-type-animated loading" role="dialog"></div>',
					defaultButtons: false,
					onContentReady: function () {

						var jc = this;
						$.post(app.appURL+'cluster_tweets', {cid: cid, index: app.session.s_index, obj: JSON.stringify(ev)}, function(response){
							var html = self.get_tweets_html(response, 'static_tweet_box', cid);
							self.delegateEvents();
							jc.setContent(html);
					}, 'json');
					},
					buttons: {
						cancel: {
							text: 'CLOSE',
							btnClass: 'btn-cancel'
						}
					}
				});
			return false;
		},
		get_tweets_html: function(response, classes, cid){
			var html = "";
			var template = _.template($("#tpl-item-tweet").html());
			$.each(response.tweets.results, function(i, tweet){
				var imgs = "";
				var t_classes = classes;
				if(response.event_tweets){
					var detected = false;
					$.each(response.event_tweets.results, function(i2, t){
						if(t._source.id_str===tweet._source.id_str){
							detected=true;
							return false;
						}
					});
					if(!detected){
						t_classes+= ' yellow-tweet';
					}
				}
				if('extended_entities' in tweet._source){
				  $.each(tweet._source.extended_entities.media, function(i, media){
									var ext = "jpg";
									if(media.media_url.endsWith("png")){
										ext = "png";
									}
										// imgs += '<a href="http://localhost/TwitterImages/'+app.session.s_index+'/'+tweet._source.id_str+"_"+i+'.'+ext+'" target="_blank"><img style="margin:2px;max-height:150px;width:auto;" src="http://localhost/TwitterImages/'+app.session.s_index+'/'+tweet._source.id_str+"_"+i+'.'+ext+'"></a>'
										imgs += '<a href="'+app.imagesURL+app.session.s_index+'/'+tweet._source.id_str+"_"+i+'.'+ext+'" target="_blank"><img style="margin:2px;max-height:150px;width:auto;" src="'+app.imagesURL+app.session.s_index+'/'+tweet._source.id_str+"_"+i+'.'+ext+'"></a>'
				  });
				}
				var state = tweet._source['session_'+app.session.s_name];
				if(state === "confirmed"){
					state = '<span class="badge badge-success">'+state+'</span>';
				}else if (state === "negative"){
					state = '<span class="badge badge-danger">'+state+'</span>';
				}else{
					state = '<span class="badge badge-secondary">'+state+'</span>';
				}
            	html += template({
					tid: tweet._id,
                              name: tweet._source.user.name,
                              screen_name: tweet._source.user.screen_name,
                              created_at: tweet._source.created_at,
                              link: tweet._source.link,
                              text:  tweet._source.text,
							  classes: t_classes,
                              images: imgs,
								state: state
                            });
          	});
			if(response.tweets.scroll_size>0){
				html += '<div class="pix-margin-top-10"><a href="#" class="btn btn-lg btn-outline-success full_width scroll_tweets" data-scroll="'+response.tweets.scroll_size+'" data-sid="'+response.tweets.sid+'"> <strong>Load more tweets</strong> </a></div>';
			}
			return html;
		},
		display_tweets: function(response, t0, eid){
			var html = '';
			html += '<div class="col-12 pix-padding-top-30 pix-padding-bottom-30">\n' +
				'                    <a class="btn btn-lg btn-success pix-white fly shadow scale btn_filter" data-eid="' + eid + '" data-state="confirmed" href="#" role="button"><strong>Confirmed</strong></a>\n' +
				'                    <a class="btn btn-lg btn-danger pix-white fly shadow scale btn_filter" data-eid="' + eid + '" data-state="negative" href="#" role="button"><strong>Negative</strong></a>\n' +
				'                    <a class="btn btn-lg btn-primary pix-white fly shadow scale btn_filter" data-eid="' + eid + '" data-state="proposed" href="#" role="button"><strong>Proposed</strong></a>\n' +
		'              </div>';
        	html += this.get_tweets_html(response, '');
			var chtml = "";
			var cbtn = "", state_btns="";
			var i = 0;
			if(response.clusters) {
                $.each(response.clusters, function (i, cluster) {
                    if (i >= 40) {
                        return false;
                    }
                    i++;
                    var cbg = "";
                    if (cluster.size > cluster.doc_count) {
                        cbg = 'yellow-tweet';
                    }
                    if (eid) {
                        cbtn = '<a href="#" class="btn btn-primary btn-flat cluster_tweets" data-eid="' + eid + '" data-cid="' + cluster.key + '"><strong>Show tweets</strong></a>';
                        state_btns = '<div class="cluster_state_btns">';
                        state_btns += '<a href="#" class="btn btn-outline-success cluster_state" data-state="confirmed" data-cid="' + cluster.key + '"><strong>Confirmed</strong></a>';
                        state_btns += ' <a href="#" class="btn btn-outline-danger cluster_state" data-state="negative" data-cid="' + cluster.key + '"><strong>Negative</strong></a>';
                        state_btns += '</div>';
                    }
                    chtml += '<div class="card p-3 ' + cbg + '">' +
                        '<img class="card-img-top" src="' + app.imagesURL + app.session.s_index + '/' + cluster.image + '" alt="">' +
                        state_btns +
                        '<div class="card-body">' +
                        '<p class="card-text">' + cluster.doc_count + ' related tweets contain this image</p>' +
                        // '<p class="card-text">'+cluster.size2+' related tweets contain this image</p>'+
                        '<p class="card-text">Cluster size: ' + cluster.size + '</p>' +
                        '<p class="card-text">Cluster ID: ' + cluster.key + '</p>' +
                        cbtn +

                        '</div>' +
                        '</div>';
                });
                $('#eventsClusters').html(chtml);
            }
			$('#tweets_result').html(html);
			$('.loading_text').fadeOut('slow');
			$('#tweets_results').fadeIn('slow');
			if(t0) {
                var t1 = performance.now();
                var time = (t1 - t0) / 1000;
                var roundedString = time.toFixed(2);
                $('#res_num').html(response.tweets.total);
                $('#res_time').html(roundedString);
            }

		},
	tweet_state: function(e){
		e.preventDefault();
		var tid = $(e.currentTarget).data("tid");
		var val = $(e.currentTarget).data("val");
		var el = $(e.currentTarget).closest('.media-body').find('.t_state');
		console.log(el);
		$.post(app.appURL+'mark_tweet', {tid: tid, index: app.session.s_index, session: app.session.s_name, val: val}, function(response){
			console.log(response);
			var state = val;
				if(state === "confirmed"){
					state = '<span class="badge badge-success">'+state+'</span>';
				}else if (state === "negative"){
					state = '<span class="badge badge-danger">'+state+'</span>';
				}else{
					state = '<span class="badge badge-secondary">'+state+'</span>';
				}
				el.html(state);
		}, 'json');
		return false;
	},
    scroll_tweets: function(e){
        e.preventDefault();
        var scroll_size = $(e.currentTarget).data("scroll");
		var sid = $(e.currentTarget).data("sid");
		var btn_area = $(e.currentTarget).parent();
		var self = this;
        var data = [];
        data.push({name: "index", value: app.session.s_index});
        data.push({name: "scroll_size", value: scroll_size});
        data.push({name: "sid",  value: sid});
        $.post(app.appURL+'tweets_scroll', data, function(response){
            var html = self.get_tweets_html(response, '');
            btn_area.replaceWith(html);
          }, 'json').fail(function() {
              $('.loading_text').fadeOut('slow');
                $.confirm({
                    title: 'Error',
                    boxWidth: '600px',
                    theme: 'pix-danger-modal',
                    backgroundDismiss: true,
                    content: "An error was encountered while connecting to the server, please try again.<br>Error code: tweets__tweets_submit",
                    buttons: {
                        cancel: {
                            text: 'CLOSE',
                            btnClass: 'btn-cancel',
                        }
                    }
                });
            });
        return false;
    },
	cluster_state: function(e){
    	e.preventDefault();
    	var state = $(e.currentTarget).data("state");
    	var cid = $(e.currentTarget).data("cid");
    	var data = [];
		data.push({name: "index", value: app.session.s_index});
		data.push({name: "session", value: app.session.s_name});
		data.push({name: "state", value: state});
		data.push({name: "cid", value: cid});
		var jc = $.confirm({
				theme: 'pix-default-modal',
				title: 'Changing tweets state',
				boxWidth: '600px',
				useBootstrap: false,
				backgroundDismiss: false,
				content: 'Please Don\'t close the page.<div class=" jconfirm-box jconfirm-hilight-shake jconfirm-type-default  jconfirm-type-animated loading" role="dialog"></div>',
				defaultButtons: false,
				buttons: {
					cancel: {
						text: 'OK',
						btnClass: 'btn-cancel'
					}
				}
			});
		$.post(app.appURL+'mark_cluster', data, function(response){
			jc.close();
		}).fail(function() {
            jc.close();
            $.confirm({
                title: 'Error',
                boxWidth: '600px',
                theme: 'pix-danger-modal',
                backgroundDismiss: true,
                content: "An error was encountered while connecting to the server, please try again.",
                buttons: {
                    cancel: {
                        text: 'CANCEL',
                        btnClass: 'btn-cancel'
                    }
                }
            });
        });
    	return false;
	},
	filter_tweets: function(e){
	    e.preventDefault();
	    var eid = $(e.currentTarget).data("eid");
	    var ev = app.eventsCollection.get({ cid: eid }).toJSON();
	    var state = $(e.currentTarget).data("state");
	    var session = 'session_'+app.session.s_name;
	    var self = this;
	    $('#tweets_results').fadeOut('slow');
	  $('.loading_text').fadeIn('slow');
	  var t0 = performance.now();
	    $.post(app.appURL+'event_filter_tweets', {obj: JSON.stringify(ev), index: app.session.s_index, state:state, session: session}, function(response){
			self.display_tweets(response, t0, eid);
		}, 'json');
	    return false;
    }
});
