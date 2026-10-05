namespace Hammer5Tools.Core.Tests.Hotkeys;

using Hammer5Tools.Core.Hotkeys;

public class HotkeyDocumentTests
{
    private const string SampleKeybindings = """
        <!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
        {
        	m_InputMacros =
        	[
        		{ m_Name = "SELECTION_ADD_KEY"		m_Input = "Shift"	},
        		{ m_Name = "TOGGLE_SNAPPING_KEY"	m_Input = "Ctrl"	},
        	]

        	m_Bindings =
        	[
        		{ m_Context = "HammerApp"	m_Command = "FileSave"	m_Input = "Ctrl+S"	},
        		{ m_Context = "HammerApp"	m_Command = "FileOpen"	m_Input = "Ctrl+O"	},
        		{ m_Context = "HammerEditorSession"	m_Command = "ClearSelection"	m_Input = "Esc"	},
        	]
        }
        """;

    [Test]
    public async Task EditsPreserveUnknownDocumentAndBindingFields()
    {
        var text = SampleKeybindings.Replace("m_Bindings =", "custom_metadata = { value = 42 }\nm_Bindings =")
            .Replace("m_Command = \"FileSave\"", "m_Command = \"FileSave\" custom_flag = true");
        var document = HotkeyDocument.Parse(text);
        document.SetBinding("HammerApp", "FileSave", "Ctrl+Alt+S");
        await Assert.That(document.Serialize()).Contains("custom_metadata");
        await Assert.That(document.Serialize()).Contains("custom_flag");
    }

    [Test]
    public async Task ParseExtractsMacrosAndBindings()
    {
        var doc = HotkeyDocument.Parse(SampleKeybindings);

        await Assert.That(doc.Macros).Count().IsEqualTo(2);
        await Assert.That(doc.Macros[0].Name).IsEqualTo("SELECTION_ADD_KEY");
        await Assert.That(doc.Macros[0].Input).IsEqualTo("Shift");

        await Assert.That(doc.Bindings).Count().IsEqualTo(3);
        await Assert.That(doc.Bindings[0].Command).IsEqualTo("FileSave");
        await Assert.That(doc.Bindings[0].Input).IsEqualTo("Ctrl+S");

        await Assert.That(doc.Contexts).Count().IsEqualTo(2);
    }

    [Test]
    public async Task RoundTripMaintainsBindings()
    {
        var doc1 = HotkeyDocument.Parse(SampleKeybindings);
        doc1.SetBinding("HammerApp", "FileSave", "Ctrl+Alt+S");

        var serialized = doc1.Serialize();
        var doc2 = HotkeyDocument.Parse(serialized);

        await Assert.That(doc2.Bindings).Count().IsEqualTo(3);
        var saveBinding = doc2.Bindings.First(b => b.Command == "FileSave");
        await Assert.That(saveBinding.Input).IsEqualTo("Ctrl+Alt+S");
    }
}
