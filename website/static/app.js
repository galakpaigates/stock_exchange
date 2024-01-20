try 
{
    // show and hide password
    document.getElementById("showPasswords").addEventListener("click", () =>
    {
        document.querySelectorAll('.passwordInput').forEach((input) =>
        {
            if (input.type === 'password')
                input.type = 'text';
            else 
                input.type = 'password';
        });
    })
}
catch (error)
{
    // pass
}

try
{
    document.getElementById('profile-picture-input').addEventListener('change', (event) => 
    {
        const selected_profile_picture = event.target.files[0]

        const read_file = new FileReader()
        read_file.readAsDataURL(selected_profile_picture)
        read_file.addEventListener('load', () =>
        {
            document.getElementById('view-profile-picture-div').innerHTML = `<img style="max-width: 90vw; max-height: 80vh; margin-bottom: 50px;" src="${read_file.result}" alt="Selected Image">`
        })


    })
}
catch (error)
{
    // pass
}