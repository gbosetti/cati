class TopRetweetsModule extends SearchModule{

    constructor(containerSelector, client) {

        super(containerSelector);
        this.client = client;
    }

    loadTweets(data){

        this.enableLoading();

        var query = data.filter(item => {return item.name == "word"})[0].value;
        if(query && query.trim() != ""){ //If the user has entered at least a keyword

            this.requestReTweets(data).then(
                res => {
                    this.presentRetweets(res.aggregations.top_text.buckets, this.containerSelector);
                    this.disableLoading();
                },
                err => { //In case of failing
                    this.clearContainer(this.containerSelector);
                    this.showNoRetweetsFound(this.containerSelector);
                    this.disableLoading();
                }
            );
        }
        else{
            this.requestReTweets(data).then(
                res => {
                    this.presentRetweets(res.aggregations.top_text.buckets, this.containerSelector);
                    this.disableLoading();
                },
                err => { //In case of failing
                    this.clearContainer(this.containerSelector);
                    this.showNoRetweetsFound(this.containerSelector);
                    this.disableLoading();
            });
        }
    }

    presentRetweets(res, selector){

        var repeated_tweets = res.filter(elem => elem.doc_count > 1); //Sometimes the bockets are conformed by just 1 tweet

        if(repeated_tweets.length>0){

            try{
                $(".top-retweets-header").text("Top " + repeated_tweets.length + " retweets");

                var html = this.client.get_retweets_html(repeated_tweets);

                $(selector).html(html);
            }catch(err){console.log(err)}
        }
        else{
            $(this.containerSelector).html("");
            this.showNoRetweetsFound(this.containerSelector);
            this.disableLoading();
        }
    }

    showNoRetweetsFound(containerSelector){
        $(containerSelector).html("Sorry, no re-tweets were found under this criteria.");
    }

    requestReTweets(data){

        return new Promise((resolve, reject) => {
            $.post(app.appURL+'top_retweets', data, (response) => {
                resolve(response);
            }, 'json').fail((err)=>{
                console.log("ERROR", err);
                this.client.cnxError(err);
                reject(err)
            });
        });
    }
}
