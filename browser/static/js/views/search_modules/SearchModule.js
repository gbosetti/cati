class SearchModule{

    constructor(containerSelector, spinnerClassName) {

        this.containerSelector = containerSelector;
        this.spinnerClassName = spinnerClassName || 'spinner-default';
    }

    enableLoading(){

        //console.log("Enabling loading at: ",this.containerSelector);
        var target = document.querySelector(this.containerSelector);
            target.style["min-height"] = "500px";

        var spinnerColor = '#677079'; //this.hasLightBackground($(target).css("background-color"))? '#677079': '#ffffff';
        new Spinner({
            lines: 13, // The number of lines to draw
            length: 50, // The length of each line
            width: 15, // The line thickness
            radius: 45, // The radius of the inner circle
            corners: 1, // Corner roundness (0..1)
            speed: 1, // Rounds per second
            rotate: 0,
            color: spinnerColor,
            className: this.spinnerClassName
        }).spin(target);
    }

    disableLoading(){

        var elem = document.querySelector(this.containerSelector);
        if(elem != undefined && elem != null) { elem.style["min-height"] = "0px"; }
        $(this.containerSelector + " ." + this.spinnerClassName).remove();
    }

    loadTweets(data){
        // subclass responsibility
    }
}

