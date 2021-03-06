app.views.review = Backbone.View.extend({
	template: _.template($("#tpl-page-events").html()),
	events: {
		'click .export_tweets': 'export_tweets',
		'click .tweet_state': 'tweet_state',
		'click .scroll_tweets': 'scroll_tweets',
		'click .btn_review': 'review_tweets',
		'click .clear_session_annotations': 'clear_session_annotations'
	},
	initialize: function() {
	    this.updateEventImages();
		//var handler = _.bind(this.render, this);
	},
	updateEventImages: function(){


	    /*app.eventsCollection = new app.collections.events();
			this.imagesURL = 'http://localhost:5000/static/images/';
			if (localStorage.getItem('session_id') !== null) {
				var sessionString = localStorage.getItem('session');
				this.session = JSON.parse(sessionString);
				this.session_id = localStorage.getItem('session_id');
				if(this.session.events){
					var collection = JSON.parse(this.session.events);
					// console.log(collection);
					this.eventsCollection.add_json_events(collection);
				}
			}
			if (localStorage.getItem('image_path') !== null) {
				this.imagesPath = localStorage.getItem('image_path');
			}*/
	},
	render: function(){
		var html = this.template({});
		this.$el.html(html);
		this.delegateEvents();
        this.updateSessionData();

		return this;
	},
	updateSessionData: function(){
	    app.views.mabed.prototype.setSessionTopBar();
        app.views.mabed.prototype.getClassificationStats();
	},
	export_tweets: function(e){
	    try{
            e.preventDefault();
            var win = window.open(app.appURL+'export_confirmed_tweets?session='+app.session_id, '_blank');
        }catch(err){
            console.log("Error:", err)
        }
		return false;
	},
	clear_session_annotations: function(evt){

        evt.preventDefault();

        if ( confirm( "Are you sure you want to clear all the annotations? These changes can not be reversed." ) ) {

            var data = [];
                data.push({name: "index", value: app.session.s_index});
                data.push({name: "session", value: "session_" + app.session.s_name});

            $.post(app.appURL+'clear_session_annotations', data, (response) => {
                if(response){
                    alert("The status of all documents has been reset.");
                    this.updateSessionData();
                }
            }, 'json').fail(function() {
                this.clear_session_annotations_error();
            });
        }
	},
	clear_session_annotations_error: function(evt){
        alert("An error has occurred. Please, try again.")
	},
	review_tweets: function(e){
		e.preventDefault();
		var state = $(e.currentTarget).data("state");
		this.load_tweets(state);
		return false;
	},
	load_tweets: function(state){
		$('#tweets_results').fadeOut('slow');
		  $('.loading_text').fadeIn('slow');
		  var t0 = performance.now();
		  var data = [];
		  data.push({name: "index", value: app.session.s_index});
		  data.push({name: "session", value: app.session.s_name});
		  data.push({name: "state", value: state});
		  var self = this;
		  $.post(app.appURL+'tweets_state', data, function(response){
			self.display_tweets(response, t0, data[0].value);
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
	},
	/*classify_tweets: function(){
	    var html = $("#tpl-classify-tweets").html()
	    console.log(html)
        return html
	},*/
	get_tweets_html: function(response, classes, cid){
        var html = "";
        var template = _.template($("#tpl-item-tweet").html());
        $.each(response.tweets.results, function(i, tweet){
            var imgs = "";
            var t_classes = classes;
            if(response.search_tweets){
                var detected = false;
                $.each(response.search_tweets, function(i2, t){
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
                          //todo change image sources
                        imgs += '<a href="'+app.imagesURL+app.imagesPath+'/'+tweet._source.id_str+"_"+i+'.'+ext+'" target="_blank"><img style="margin:2px;max-height:150px;width:auto;" src="'+app.imagesURL+app.imagesPath+'/'+tweet._source.id_str+"_"+i+'.'+ext+'"></a>'
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
    display_tweets: function(response, t0, word){

        var html = this.get_tweets_html(response, '');
        $('.individual_tweets_result:visible:last').html(html);
        $('.loading_text:visible:last').fadeOut('slow');
        $('.tweets_results:visible:last').fadeIn('slow');
        if(t0){
            var t1 = performance.now();
            var time = (t1 - t0) / 1000;
            var roundedString = time.toFixed(2);
            $('.res_num').html(response.tweets.total);
            $('.res_time').html(roundedString);
        }
    },
	tweet_state: function(e){
		e.preventDefault();
		var tid = $(e.currentTarget).data("tid");
		var val = $(e.currentTarget).data("val");
		var el = $(e.currentTarget).closest('.media-body').find('.t_state');
		$.post(app.appURL+'mark_tweet', {tid: tid, index: app.session.s_index, session: app.session.s_name, val: val}, function(response){
			var state = val;
				if(state === "confirmed"){
					state = '<span class="badge badge-success">'+state+'</span>';
				}else if (state === "negative"){
					state = '<span class="badge badge-danger">'+state+'</span>';
				}else{
					state = '<span class="badge badge-secondary">'+state+'</span>';
				}
				el.html(state);
            app.views.mabed.prototype.getClassificationStats();
		}, 'json').fail(function() {
                        $.confirm({
                            title: 'Error',
                            boxWidth: '600px',
                            theme: 'pix-danger-modal',
                            backgroundDismiss: true,
                            content: "An error was encountered while connecting to the server, please try again.<br>Error code: tweets__tweet_state",
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
    }
});
