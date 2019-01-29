app.views.beta2 = Backbone.View.extend({
    template: _.template($("#tpl-page-beta2").html()),
    events: {
        'submit #run_mabed': 'run_mabed',
        'click .start_btn': 'start_btn'
    },
    initialize: function() {
        var handler = _.bind(this.render, this);
    },
    render: function(){
        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();

        // Step 1
        this.get_stats();
        // Step 2
        // this.get_keywords();
        // Step 3
        // this.get_sse();
        // Step 4
        // this.get_elbow();
        // this.event_sse("123");

        return this;
    },
    get_stats: function(){
        var words = '';
        var self = this;
        var count = 1;

        app.eventsCollection.each(function(event){
            self.event_stats(event, count);
            count++;
        });
        app.eventsCollection.each(function(event){
            var att = event.attributes;
            words += att.main_term + ' ';
            $.each(att.related_terms, function(i, term){
                if(term.word.length>2){
                    words += term.word + ' ';
                }
            });
        });
        $.post(app.appURL+'get_all_count', {index: app.session.s_index}, function(response){
            var all_count = parseInt(response.count);
            $('#all_num').html(all_count);
            $.post(app.appURL+'get_words_count', {index: app.session.s_index, words: words}, function(response){
                var detected_count = parseInt(response.count);
                var non_detected_count = all_count - detected_count;
                $('#non_detected_num').html(non_detected_count);
                var percentage_num = 100*(detected_count*1.0/parseFloat(all_count));
                $('#percentage_num').html(percentage_num);
            }, 'json');

        }, 'json');

    },
    event_stats: function(event, count){
        var html = "";


        var sum = 0;



        var s_ev = event.toJSON();
        $.post(app.appURL+'event_tweets_count', {obj: JSON.stringify(s_ev), index: app.session.s_index}, function(response){
            var att = event.attributes;

            html +='<tr>';
            // html +='<th scope="row">'+count+'</th>';
            html +='<td>'+att.start_date+' '+att.end_date+'</td>';
            html +='<td>'+att.main_term+'</td>';
            html +='<td>';
            $.each(att.related_terms, function(i, term){
                html += '<span class="badge badge-secondary">'+term.word+'</span> ';
            });
            html +='</td>';
            html +='<td>'+response.count+'</td>';
            html +='<td>'+parseFloat(response.percentage).toFixed(2)+'</td>';
            html +='<td><a href="#" data-cid="'+event.cid+'" class="btn btn-sm light-green-bg pix-white fly shadow start_btn"><i class="pixicon-play"></i><strong class="">Run</strong></a></td>';
            html +='</tr>';

            // console.log(response);
            sum += response.count;
            // console.log(sum);
            $('#main_table').append(html);
        }, 'json');

    },
    start_btn: function(e){
        e.preventDefault();
        var cid = $(e.currentTarget).data("cid");
        this.get_keywords(cid);
        return false;
    },
    get_keywords: function(cid=""){
        var self = this;
        counter = 0;
        app.eventsCollection.each(function(event){
            if(event.cid===cid) {
                var words = '';
                var att = event.attributes;
                words += att.main_term + ' ';
                var related_html = '';
                // $.each(att.related_terms, function (i, term) {
                //     words += term.word + ' ';
                //     related_html += '<span class="badge badge-secondary">' + term.word + '</span> ';
                // });
                words = words.replace(/,/g, "");
                // console.log(words);
                var sd = new Date(event.get('start_date'));
                var ed = new Date(event.get('end_date'));
                // console.log(sd.getTime());
                // console.log(ed.getTime());

                var el = 'chartContainer_'+counter;

                $.post(app.appURL + 'get_keywords', {
                    sd: sd.getTime(),
                    ed: ed.getTime(),
                    words: words,
                    count: 20,
                    index: app.session.s_index
                }, function (response) {
                    console.log(response);

                    var new_html = '';
                    $.each(response.newKeywords, function (i, term) {
                        var val = parseFloat(term[1]).toPrecision(4)
                        new_html += '<span class="badge badge-success">' + term[0] + ' (' + val + ')</span> ';
                    });
                    var html = '<tr>' +
                        '    <td>' + att.main_term + '</td>' +
                        // '    <td>' + related_html + '</td>' +
                        '    <td>' + new_html + '</td>' +
                        '</tr>';
                    $('#keywords').append(html);
                    self.event_sse(response.newKeywords, event, el);
                }, 'json');

            }

            counter++;

        });


    },
    event_sse: function(newkeywords, event, el){
        var self = this;
        // app.eventsCollection.each(function(event){
            var att = event.attributes;
            var s_ev = event.toJSON();
            // if(event.cid==="c3"){
                var sd = new Date(event.get('start_date'));
                var ed = new Date(event.get('end_date'));
                var keywords = {words:newkeywords}

                // var res = [{"x":0,"y":42.96528552571478},{"x":1,"y":41.19347176196189},{"x":2,"y":40.62345952886545},{"x":3,"y":40.71212354106569},{"x":4,"y":40.8120563957318},{"x":5,"y":40.84488158761365},{"x":6,"y":40.70839660331585},{"x":7,"y":40.95958705033671},{"x":8,"y":40.9779656013633},{"indexLabel":"Optimal number of new keywords","markerColor":"red","x":9,"y":41.00609962114167},{"x":10,"y":40.73695314180544},{"x":11,"y":40.741808187305374},{"x":12,"y":40.67461579509566},{"x":13,"y":40.63396858765199},{"x":14,"y":40.63396858765199},{"x":15,"y":40.4975788071574},{"x":16,"y":40.452602086961676},{"x":17,"y":40.209293318723155},{"x":18,"y":40.22040943410529},{"x":19,"y":40.26861736901534}];
                // self.get_elbow(res);


                 var html = '<tr>' +
                        '    <td>' + att.main_term + '</td>' +
                        '    <td><div id="'+el+'" style="height: 370px; width: 950px;"></div></td>' +
                        '</tr>';

                $('#elbow_results').append(html);
                // var el = 'chartContainer_'+counter;



                // var response = {"elbow":2,"sse":{"0":43.61416044777739,"1":43.20544864756074,"2":36.324743262392936,"3":43.189768564708004,"4":42.71573578968671,"5":43.220329582120925,"6":41.42366922699849,"7":42.80747327225816,"8":42.40977088779801,"9":42.42765192668555,"10":42.914549802496786,"11":42.228479417012984,"12":42.63822873425157,"13":42.540635633242694,"14":42.69521259846636,"15":42.964340567968584,"16":42.774479124031245,"17":42.02633487297787,"18":41.402080781957615,"19":42.16676661672122},"sse2":[[0,[43.61416044777739,"f\u00eates"]],[1,[43.20544864756074,"votez"]],[2,[36.324743262392936,"oui"]],[3,[43.189768564708004,"couleurs"]],[4,[42.71573578968671,"m\u00e9tro"]],[5,[43.220329582120925,"djaldebaran1"]],[6,[41.42366922699849,"mettre"]],[7,[42.80747327225816,"heures"]],[8,[42.40977088779801,"coeur"]],[9,[42.42765192668555,"partie"]],[10,[42.914549802496786,"ambiance"]],[11,[42.228479417012984,"bient\u00f4t"]],[12,[42.63822873425157,"voyage"]],[13,[42.540635633242694,"retrouver"]],[14,[42.69521259846636,"20minutes"]],[15,[42.964340567968584,"illuminations"]],[16,[42.774479124031245,"le_progres"]],[17,[42.02633487297787,"lyonmag"]],[18,[41.402080781957615,"nuit"]],[19,[42.16676661672122,"froid"]]],"sse_points":[{"label":"oui","x":0,"y":36.324743262392936},{"label":"nuit","x":1,"y":41.402080781957615},{"indexLabel":"Optimal number of new keywords","label":"mettre","markerColor":"red","x":2,"y":41.42366922699849},{"label":"lyonmag","x":3,"y":42.02633487297787},{"label":"froid","x":4,"y":42.16676661672122},{"label":"bient\u00f4t","x":5,"y":42.228479417012984},{"label":"coeur","x":6,"y":42.40977088779801},{"label":"partie","x":7,"y":42.42765192668555},{"label":"retrouver","x":8,"y":42.540635633242694},{"label":"voyage","x":9,"y":42.63822873425157},{"label":"20minutes","x":10,"y":42.69521259846636},{"label":"m\u00e9tro","x":11,"y":42.71573578968671},{"label":"le_progres","x":12,"y":42.774479124031245},{"label":"heures","x":13,"y":42.80747327225816},{"label":"ambiance","x":14,"y":42.914549802496786},{"label":"illuminations","x":15,"y":42.964340567968584},{"label":"couleurs","x":16,"y":43.189768564708004},{"label":"votez","x":17,"y":43.20544864756074},{"label":"djaldebaran1","x":18,"y":43.220329582120925},{"label":"f\u00eates","x":19,"y":43.61416044777739}]}
                // var response = {"elbow":3,"sse":{"0":44.827641895811375,"1":44.40818532849946,"2":37.58633812477311,"3":44.385508426027094,"4":43.921264239851865,"5":44.4130232854449,"6":42.644302348536705,"7":44.00902150450123,"8":43.622575883211475,"9":43.63696685804222,"10":44.116333317530916,"11":43.44154824281423,"12":43.8431860801336,"13":43.746913169646525,"14":43.91258345352168,"15":44.16929528578595,"16":43.98515838854853,"17":43.243741318836335,"18":42.6295851697392,"19":43.37857196360737,"20":39.26548926252214,"21":42.70680925494733,"22":23.700607616816637,"23":44.01209428611428,"24":43.9154102685453,"25":44.52328212898601,"26":43.88242245459838,"27":43.856395267946766,"28":44.157734389120975,"29":39.319465341886485,"30":43.50069249250362,"31":43.66462922287357,"32":43.76688265207354,"33":43.66076279616175,"34":43.75283654820772,"35":44.402869153825925,"36":44.11208969710302,"37":43.94790465544124,"38":44.31152640897885,"39":44.1792562800719},"sse2":[[0,[44.827641895811375,"f\u00eates"]],[1,[44.40818532849946,"votez"]],[2,[37.58633812477311,"oui"]],[3,[44.385508426027094,"couleurs"]],[4,[43.921264239851865,"m\u00e9tro"]],[5,[44.4130232854449,"djaldebaran1"]],[6,[42.644302348536705,"mettre"]],[7,[44.00902150450123,"heures"]],[8,[43.622575883211475,"coeur"]],[9,[43.63696685804222,"partie"]],[10,[44.116333317530916,"ambiance"]],[11,[43.44154824281423,"bient\u00f4t"]],[12,[43.8431860801336,"voyage"]],[13,[43.746913169646525,"retrouver"]],[14,[43.91258345352168,"20minutes"]],[15,[44.16929528578595,"illuminations"]],[16,[43.98515838854853,"le_progres"]],[17,[43.243741318836335,"lyonmag"]],[18,[42.6295851697392,"nuit"]],[19,[43.37857196360737,"froid"]],[20,[39.26548926252214,"bonjour"]],[21,[42.70680925494733,"parti"]],[22,[23.700607616816637,"vous"]],[23,[44.01209428611428,"gones"]],[24,[43.9154102685453,"magique"]],[25,[44.52328212898601,"magie"]],[26,[43.88242245459838,"garde"]],[27,[43.856395267946766,"pr\u00eat"]],[28,[44.157734389120975,"sp\u00e9ciale"]],[29,[39.319465341886485,"aujourd'hui"]],[30,[43.50069249250362,"trouve"]],[31,[43.66462922287357,"route"]],[32,[43.76688265207354,"trouver"]],[33,[43.66076279616175,"d'avoir"]],[34,[43.75283654820772,"heureux"]],[35,[44.402869153825925,"blogueuse"]],[36,[44.11208969710302,"sp\u00e9cial"]],[37,[43.94790465544124,"bout"]],[38,[44.31152640897885,"parcours"]],[39,[44.1792562800719,"profitez"]]],"sse_points":[{"label":"vous","x":0,"y":23.700607616816637},{"label":"oui","x":1,"y":37.58633812477311},{"label":"bonjour","x":2,"y":39.26548926252214},{"indexLabel":"Optimal number of new keywords","label":"aujourd'hui","markerColor":"red","x":3,"y":39.319465341886485},{"label":"nuit","x":4,"y":42.6295851697392},{"label":"mettre","x":5,"y":42.644302348536705},{"label":"parti","x":6,"y":42.70680925494733},{"label":"lyonmag","x":7,"y":43.243741318836335},{"label":"froid","x":8,"y":43.37857196360737},{"label":"bient\u00f4t","x":9,"y":43.44154824281423},{"label":"trouve","x":10,"y":43.50069249250362},{"label":"coeur","x":11,"y":43.622575883211475},{"label":"partie","x":12,"y":43.63696685804222},{"label":"d'avoir","x":13,"y":43.66076279616175},{"label":"route","x":14,"y":43.66462922287357},{"label":"retrouver","x":15,"y":43.746913169646525},{"label":"heureux","x":16,"y":43.75283654820772},{"label":"trouver","x":17,"y":43.76688265207354},{"label":"voyage","x":18,"y":43.8431860801336},{"label":"pr\u00eat","x":19,"y":43.856395267946766},{"label":"garde","x":20,"y":43.88242245459838},{"label":"20minutes","x":21,"y":43.91258345352168},{"label":"magique","x":22,"y":43.9154102685453},{"label":"m\u00e9tro","x":23,"y":43.921264239851865},{"label":"bout","x":24,"y":43.94790465544124},{"label":"le_progres","x":25,"y":43.98515838854853},{"label":"heures","x":26,"y":44.00902150450123},{"label":"gones","x":27,"y":44.01209428611428},{"label":"sp\u00e9cial","x":28,"y":44.11208969710302},{"label":"ambiance","x":29,"y":44.116333317530916},{"label":"sp\u00e9ciale","x":30,"y":44.157734389120975},{"label":"illuminations","x":31,"y":44.16929528578595},{"label":"profitez","x":32,"y":44.1792562800719},{"label":"parcours","x":33,"y":44.31152640897885},{"label":"couleurs","x":34,"y":44.385508426027094},{"label":"blogueuse","x":35,"y":44.402869153825925},{"label":"votez","x":36,"y":44.40818532849946},{"label":"djaldebaran1","x":37,"y":44.4130232854449},{"label":"magie","x":38,"y":44.52328212898601},{"label":"f\u00eates","x":39,"y":44.827641895811375}]}
                // var response = {"elbow":2,"sse":{"0":43.10403910910113,"1":44.59772881554741,"2":44.378230523399054,"3":44.431179581228086,"4":39.58053361945312,"5":45.043850269189214,"6":43.669227897280166,"7":42.95454212182367,"8":45.18930182242418,"9":44.58910364587032,"10":44.15661135364581,"11":43.60517430008678,"12":44.79885248352453,"13":42.82327649937009,"14":41.97881205303227,"15":44.86525574611602,"16":42.61184931845951,"17":43.18419804661016,"18":43.75815968534068,"19":39.426953437930784,"20":44.090322941444995,"21":44.73605908000088,"22":44.657146167341566,"23":43.80532346905512,"24":42.96588449712735,"25":43.3851685034158,"26":44.86298531626931,"27":41.44000122334151,"28":43.76421475424388,"29":44.87327318290636,"30":44.57001411330052,"31":44.38919125748686,"32":44.312027523058504,"33":43.65068784945,"34":44.31770667227791,"35":43.8871991189233,"36":44.8009137795494,"37":29.04014353317082,"38":41.58463519279726,"39":43.6171062267596},"sse2":[[0,[43.10403910910113,"retrouvez"]],[1,[44.59772881554741,"illuminations"]],[2,[44.378230523399054,"le_progres"]],[3,[44.431179581228086,"heures"]],[4,[39.58053361945312,"aujourd'hui"]],[5,[45.043850269189214,"th\u00e9\u00e2tre"]],[6,[43.669227897280166,"weekend"]],[7,[42.95454212182367,"programme"]],[8,[45.18930182242418,"f\u00eates"]],[9,[44.58910364587032,"sp\u00e9ciale"]],[10,[44.15661135364581,"retrouver"]],[11,[43.60517430008678,"suite"]],[12,[44.79885248352453,"couleurs"]],[13,[42.82327649937009,"d\u00e9couvrir"]],[14,[41.97881205303227,"concert"]],[15,[44.86525574611602,"assurgerance"]],[16,[42.61184931845951,"c'\u00e9tait"]],[17,[43.18419804661016,"attend"]],[18,[43.75815968534068,"froid"]],[19,[39.426953437930784,"no\u00ebl"]],[20,[44.090322941444995,"commence"]],[21,[44.73605908000088,"profiter"]],[22,[44.657146167341566,"offrir"]],[23,[43.80532346905512,"\u00e9dition"]],[24,[42.96588449712735,"mettre"]],[25,[43.3851685034158,"d\u00e9couvrez"]],[26,[44.86298531626931,"grotteslabalme"]],[27,[41.44000122334151,"lieu"]],[28,[43.76421475424388,"1\u00e8re"]],[29,[44.87327318290636,"lesillumin\u00e9s"]],[30,[44.57001411330052,"europe1"]],[31,[44.38919125748686,"retrouve"]],[32,[44.312027523058504,"magique"]],[33,[43.65068784945,"vite"]],[34,[44.31770667227791,"vivre"]],[35,[43.8871991189233,"savoir"]],[36,[44.8009137795494,"votez"]],[37,[29.04014353317082,"contre-soir\u00e9es"]],[38,[41.58463519279726,"jusqu'\u00e0"]],[39,[43.6171062267596,"leprogreslyon"]]],"sse_points":[{"label":"contre-soir\u00e9es","x":0,"y":29.04014353317082},{"label":"no\u00ebl","x":1,"y":39.426953437930784},{"indexLabel":"Optimal number of new keywords","label":"aujourd'hui","markerColor":"red","x":2,"y":39.58053361945312},{"label":"lieu","x":3,"y":41.44000122334151},{"label":"jusqu'\u00e0","x":4,"y":41.58463519279726},{"label":"concert","x":5,"y":41.97881205303227},{"label":"c'\u00e9tait","x":6,"y":42.61184931845951},{"label":"d\u00e9couvrir","x":7,"y":42.82327649937009},{"label":"programme","x":8,"y":42.95454212182367},{"label":"mettre","x":9,"y":42.96588449712735},{"label":"retrouvez","x":10,"y":43.10403910910113},{"label":"attend","x":11,"y":43.18419804661016},{"label":"d\u00e9couvrez","x":12,"y":43.3851685034158},{"label":"suite","x":13,"y":43.60517430008678},{"label":"leprogreslyon","x":14,"y":43.6171062267596},{"label":"vite","x":15,"y":43.65068784945},{"label":"weekend","x":16,"y":43.669227897280166},{"label":"froid","x":17,"y":43.75815968534068},{"label":"1\u00e8re","x":18,"y":43.76421475424388},{"label":"\u00e9dition","x":19,"y":43.80532346905512},{"label":"savoir","x":20,"y":43.8871991189233},{"label":"commence","x":21,"y":44.090322941444995},{"label":"retrouver","x":22,"y":44.15661135364581},{"label":"magique","x":23,"y":44.312027523058504},{"label":"vivre","x":24,"y":44.31770667227791},{"label":"le_progres","x":25,"y":44.378230523399054},{"label":"retrouve","x":26,"y":44.38919125748686},{"label":"heures","x":27,"y":44.431179581228086},{"label":"europe1","x":28,"y":44.57001411330052},{"label":"sp\u00e9ciale","x":29,"y":44.58910364587032},{"label":"illuminations","x":30,"y":44.59772881554741},{"label":"offrir","x":31,"y":44.657146167341566},{"label":"profiter","x":32,"y":44.73605908000088},{"label":"couleurs","x":33,"y":44.79885248352453},{"label":"votez","x":34,"y":44.8009137795494},{"label":"grotteslabalme","x":35,"y":44.86298531626931},{"label":"assurgerance","x":36,"y":44.86525574611602},{"label":"lesillumin\u00e9s","x":37,"y":44.87327318290636},{"label":"th\u00e9\u00e2tre","x":38,"y":45.043850269189214},{"label":"f\u00eates","x":39,"y":45.18930182242418}]}
                //  var res_html  = '';
                // $.each(response.sse, function (i, see_res) {
                //     var val = parseFloat(see_res).toPrecision(4)
                //     res_html += '<span class="badge badge-secondary">' + i + ' (' + val + ')</span> ';
                // });
                // var sse_html = '<tr>' +
                //     '    <td>' + att.main_term + '</td>' +
                //     '    <td>'+res_html+'</td>' +
                //     '</tr>';
                // $('#sse_results').append(sse_html);
                //
                // self.get_elbow(el, response.sse_points);
                //
                //
                $.post(app.appURL+'get_results', {obj: JSON.stringify(s_ev),keywords: JSON.stringify(newkeywords),session: app.session.s_name,index: app.session.s_index}, function(response){
                    console.log(response);
                    var results = response.newlist;
                    var phtml ='';
                    $.each(results, function(i, parr){
                        var p = parr[1][2];
                        percent = parseFloat(p.percent).toFixed(2);
                        phtml += '<b>'+p.word+ ':</b> NbE='+p.NbE+' , NbK='+p.NbK+' , NbKb='+p.NbKb+' , Percent='+percent+'<br><hr>';
                    });
                    var sse_html = '<tr>' +
                        '    <td>' + att.main_term + '</td>' +
                        '    <td>'+phtml+'</td>' +
                        '</tr>';
                    $('#sse_results').append(sse_html);
                    self.get_elbow(el, response.elbow);

                    var s5 = response.step5;
                    var s5_html = '';
                    s5_html+='<b>Event Count:</b>'+s5.eventCount + '<br>';
                    s5_html+='<b>Event Confirmed Count:</b>'+s5.eventConfirmedCount + '<br><br><br>';
                    $('#step5').html(s5_html);

                    var s5_table = '';
                    $.each(s5.testList, function(i, res){
                        var wcount = res.words.split(' ').length;
                        // testpercent = parseFloat((res.testValConfirmedCount/res.testValCount)*100).toFixed(2);
                        testpercent = parseFloat((res.testValConfirmedCount/(res.reviewedTweetsCount))*100).toFixed(2);
                        s5_table += '<tr>' +
                        '    <td>' + parseFloat(res.val).toFixed(2)+ '</td>' +
                        '    <td>'+ res.words +' ('+wcount+')</td>' +
                        '    <td>'+ res.testValCount +'</td>' +
                        '    <td>'+ res.reviewedTweetsCount +'</td>' +
                        '    <td>'+ res.testValConfirmedCount +'</td>' +
                        '    <td>'+ testpercent +'</td>' +
                        '    <td>'+ parseFloat(res.newConfirmedPersent).toFixed(2) +'</td>' +
                        '</tr>';
                    });
                    $('#step5_table').html(s5_table);

                }, 'json');



                // $.post(app.appURL+'get_sse', {obj: JSON.stringify(s_ev),keywords: JSON.stringify(keywords), sd: sd.getTime(), ed: ed.getTime(), words:"words",index: app.session.s_index}, function(response){
                //     console.log(response);
                //     var res_html  = '';
                //     $.each(response.sse, function (i, see_res) {
                //         var val = parseFloat(see_res).toPrecision(4)
                //         res_html += '<span class="badge badge-secondary">' + i + ' (' + val + ')</span> ';
                //     });
                //     var sse_html = '<tr>' +
                //         '    <td>' + att.main_term + '</td>' +
                //         '    <td>'+res_html+'</td>' +
                //         '</tr>';
                //     $('#sse_results').append(sse_html);
                //
                //     self.get_elbow(el, response.sse_points);
                //
                //     $.post(app.appURL+'get_results', {obj: JSON.stringify(s_ev),keywords: JSON.stringify(newkeywords),session: app.session.s_name,index: app.session.s_index}, function(response){
                //         console.log(response);
                //     }, 'json');
                //
                // }, 'json');


            // }

        // });
    },
    get_sse: function(){
        var self = this;
        app.eventsCollection.each(function(event){
            var s_ev = event.toJSON();
            if(event.cid==="c3"){
                var sd = new Date(event.get('start_date'));
                var ed = new Date(event.get('end_date'));
                $.post(app.appURL+'get_sse', {obj: JSON.stringify(s_ev), sd: sd.getTime(), ed: ed.getTime(), words:"words",index: app.session.s_index}, function(response){
                    console.log(response);

                }, 'json');
            }


        });
    },
    get_elbow: function(el, points){
        var chart = new CanvasJS.Chart(el, {
        animationEnabled: true,
        theme: "light2",
        axisX: {
            title: "keywords"
        },
        axisY: {
            title: "Intersection percentage"
        },
        data: [{
            type: "line",
            dataPoints: points
        }]
    });
    chart.render();
    }
});
