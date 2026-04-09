function openPlatform(key){
    window.location.href = "/my_channels?platform=" + key;
}

function editChannel(id){
    window.location.href = "/edit_channel/" + id;
}

function deleteChannel(id){
    if(confirm("Удалить канал?")){
        fetch("/delete_channel/" + id, {method:"POST"})
            .then(()=>location.reload());
    }
}