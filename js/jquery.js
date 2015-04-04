function localize(t)
{
    var format = 'YYYY/MM/DD HH:mm:ss ZZ';
    var d = new Date(t+" UTC");
    document.write(d.toLocaleString());
}
