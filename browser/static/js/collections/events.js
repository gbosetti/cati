app.collections.events = Backbone.Collection.extend({
    initialize: function(){ },
    add_event: function(mag, start_date, end_date, main_term, related_terms){
      var terms = JSON.parse(related_terms);
        res = this.add({
            mag: mag,
            start_date: start_date,
            end_date: end_date,
            main_term: main_term,
            related_terms: terms
        });

        var s_ev = res.toJSON();
        $.post(app.appURL+'event_image', {obj: JSON.stringify(s_ev), index: app.session.s_index, s_name: app.session.s_name}, function(response){
            if(response.result){
                var ext = "jpg";
                if(response.image.extended_entities.media[0].media_url.endsWith("png")){
                    ext = "png";
                }
                res.set({image: app.imagesURL+app.imagesPath+'/'+response.image.id_str+"_0"+'.'+ext});
            }else{
                res.set({image: "static/images/img.jpg"});
            }
        }, 'json');
        return res;
    },
    add_json_events: function(json){
      var self = this;
      $.each(json, function( i, value ) {
        var res = self.add({
            mag: value.mag,
            start_date: value.start_date,
            end_date: value.end_date,
            main_term: value.main_term,
            related_terms: value.related_terms
        });
        var s_ev = res.toJSON();
        $.post(app.appURL+'event_image', {obj: JSON.stringify(s_ev), index: app.session.s_index, s_name: app.session.s_name}, function(response){
            if(response.result){
                var ext = "jpg";
                if(response.image.extended_entities.media[0].media_url.endsWith("png")){
                    ext = "png";
                }
                res.set({image: app.imagesURL+app.imagesPath+'/'+response.image.id_str+"_0"+'.'+ext});
            }else{
                res.set({image: "static/images/img.jpg"});
            }
        }, 'json');
        return res;
      });
    },
    get_all_events_images: function(events){

        var event_desc = events.models.map(model => {
            var desc =model.attributes;
                desc.cid=model.cid;
                return desc;
        });

        return new Promise(function(resolve, reject) {

            $.post(app.appURL+'all_events_images', {"events": JSON.stringify(event_desc), index: app.session.s_index, s_name: app.session.s_name}, function(response){

                response.forEach(event => {

                    var ext = "jpg";
                    if(event.image_src.endsWith("png")){
                        ext = "png";
                    }
                    event.image = app.imagesURL+app.imagesPath+'/'+event.image_id+"_0"+'.'+ext;
                });
                resolve(response);
            }, 'json');
        });
    },
    get_timeline_events: function(){
          var self = this;

          return new Promise((resolve, reject) => {
              var events = [];

              self.each(function(event){  //the images are not stored when the tab is reloaded

                var sd = new Date(event.get('start_date'));
                var ed = new Date(event.get('end_date'));
                var terms = '<div class="tl_btns">';
                if(event.get('related_terms')){
                  $.each(event.get('related_terms'), function(i, t){
                    terms+= '<a href="#" style="opacity:'+t.value+';" data-value="'+t.word+'" class="timeline_btn event_word_btn">'+t.word+' ('+t.value+')</a> ';
                  });
                }
                terms+="</div>";
                terms+="<div> </div>";
                terms+='<div class="timeline_options"><hr>';
                terms+='Mark event tweets as: <a href="#" data-cid="'+event.cid+'" data-status="negative" class="timeline_btn tl_options_btn options_btn_negative">negative</a> <a href="#" data-cid="'+event.cid+'" data-status="confirmed" class="timeline_btn tl_options_btn options_btn_valid">Confirmed</a>';
                terms+='</div>';

                var image = event.attributes.image; //This is most of the times, not loaded yet

                  if(!image){
                      image = "static/images/img.jpg";
                  }
                  var obj = {
                    "media": {
                      "url": image,
                      "thumbnail": image
                    },
                    "start_date": {
                      "month": sd.getMonth()+1,
                      "day": sd.getDate(),
                      "year": sd.getFullYear(),
                      "hour": sd.getHours(),
                      "minute": sd.getMinutes(),
                    },
                    "end_date": {
                      "month": ed.getMonth()+1,
                      "day": ed.getDate(),
                      "year": ed.getFullYear(),
                      "hour": ed.getHours(),
                      "minute": ed.getMinutes(),
                    },
                    "text": {
                      "headline": event.get('main_term'),
                      "text": terms
                    },
                    "unique_id": event.cid
                  };
                  events.push(obj);
              });

              //Update the images before returning the list of events, since sometimes they came in blank
              self.get_all_events_images(self).then(imagesByEvent => {

                events.forEach(event=>{
                    var matching = imagesByEvent.filter(imgByEvt => { return event.unique_id == imgByEvt.cid })[0];
                    event.media.url = matching.image;
                    event.media.thumbnail = matching.image;
                });
                 resolve({ "events": events });
              });
          });
        },
        model: app.models.event
    }
);
