app.collections.events = Backbone.Collection.extend({
    initialize: function(){},
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
        $.post(app.appURL+'event_image', {obj: JSON.stringify(s_ev), index: app.session.s_index}, function(response){
            if(response.result){
                var ext = "jpg";
                if(response.image.extended_entities.media[0].media_url.endsWith("png")){
                    ext = "png";
                }
                res.set({image: app.imagesURL+app.session.s_index+'/'+response.image.id_str+"_0"+'.'+ext});
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
        $.post(app.appURL+'event_image', {obj: JSON.stringify(s_ev), index: app.session.s_index}, function(response){
            if(response.result){
                var ext = "jpg";
                if(response.image.extended_entities.media[0].media_url.endsWith("png")){
                    ext = "png";
                }
                res.set({image: app.imagesURL+app.session.s_index+'/'+response.image.id_str+"_0"+'.'+ext});
            }else{
                res.set({image: "static/images/img.jpg"});
            }
        }, 'json');
      });
    },
    get_timeline_events: function(){
      var self = this;
      var events = [];
      self.each(function(event){
        var sd = new Date(event.get('start_date'));
        var ed = new Date(event.get('end_date'));
        var image = event.get('image');

        var terms = '<div class="tl_btns">';
        if(event.get('related_terms')){
          $.each(event.get('related_terms'), function(i, t){
            terms+= '<a href="#" style="opacity:'+t.value+';" data-value="'+t.word+'" class="timeline_btn event_word_btn">'+t.word+' ('+t.value+')</a> ';
          });
        }
        terms+="</div>";
        terms+='<div class="timeline_options"><hr>';
        terms+='Mark event tweets as: <a href="#" data-cid="'+event.cid+'" data-status="negative" class="timeline_btn tl_options_btn options_btn_negative">negative</a> <a href="#" data-cid="'+event.cid+'" data-status="confirmed" class="timeline_btn tl_options_btn options_btn_valid">Confirmed</a>';
        terms+='</div>';
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
      return { "events": events };
    },
    model: app.models.event
});
